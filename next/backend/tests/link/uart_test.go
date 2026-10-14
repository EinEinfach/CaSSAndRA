package link_test

import (
	"bufio"
	"context"
	"errors"
	"io"
	"net"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// serialRobot is the robot side of a serial line: it answers through the
// simulator and, like the firmware console, prints other lines in between.
type serialRobot struct {
	sim   *link.Sim
	noise []string // printed before every answer
	mute  bool     // read requests but never answer

	mu    sync.Mutex
	opens int
	conns []net.Conn
}

func (r *serialRobot) open() (io.ReadWriteCloser, error) {
	ours, theirs := net.Pipe()
	r.mu.Lock()
	r.opens++
	r.conns = append(r.conns, theirs)
	r.mu.Unlock()
	go func() {
		sc := bufio.NewScanner(theirs)
		for sc.Scan() {
			if r.mute {
				continue
			}
			for _, n := range r.noise {
				if _, err := io.WriteString(theirs, n+"\r\n"); err != nil {
					return
				}
			}
			reply, err := r.sim.Exchange(context.Background(), sc.Text())
			if err != nil {
				continue
			}
			if _, err := io.WriteString(theirs, reply); err != nil {
				return
			}
		}
	}()
	return ours, nil
}

// unplug closes the robot side of the current connection.
func (r *serialRobot) unplug() {
	r.mu.Lock()
	defer r.mu.Unlock()
	_ = r.conns[len(r.conns)-1].Close()
}

func (r *serialRobot) openCount() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	return r.opens
}

func exchange(t *testing.T, tr *link.LineTransport, payload string) (string, error) {
	t.Helper()
	line, err := tr.Exchange(context.Background(), protocol.Frame(payload))
	if err != nil {
		return "", err
	}
	reply, err := protocol.Unframe(line)
	if err != nil {
		t.Fatalf("reply %q: %v", line, err)
	}
	return reply, nil
}

func TestLineTransportSkipsConsoleOutput(t *testing.T) {
	robot := &serialRobot{sim: newSim(t), noise: []string{
		"AT+C: mow=1 op=1 spd=0.25",                            // firmware log line
		protocol.Frame("S,27.5,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0"), // answer to someone else
		"garbage\x00\xff",
	}}
	tr := link.NewLineTransport(robot.open, time.Second)
	defer func() { _ = tr.Close() }()

	reply, err := exchange(t, tr, "AT+V")
	if err != nil || !strings.HasPrefix(reply, "V,Sunray") {
		t.Fatalf("AT+V -> %q, %v", reply, err)
	}
	reply, err = exchange(t, tr, protocol.Stop().Encode())
	if err != nil || reply != "C" {
		t.Errorf("AT+C -> %q, %v", reply, err)
	}
	if robot.openCount() != 1 {
		t.Errorf("port opened %d times, want once", robot.openCount())
	}
}

func TestLineTransportTimesOutWithoutReply(t *testing.T) {
	robot := &serialRobot{sim: newSim(t), mute: true}
	tr := link.NewLineTransport(robot.open, 30*time.Millisecond)
	defer func() { _ = tr.Close() }()

	if _, err := exchange(t, tr, "AT+S"); !errors.Is(err, link.ErrNoReply) {
		t.Errorf("err = %v, want ErrNoReply", err)
	}
}

func TestLineTransportReopensAfterTheLineFails(t *testing.T) {
	robot := &serialRobot{sim: newSim(t)}
	tr := link.NewLineTransport(robot.open, time.Second)
	defer func() { _ = tr.Close() }()

	if _, err := exchange(t, tr, "AT+V"); err != nil {
		t.Fatal(err)
	}
	robot.unplug()
	if _, err := exchange(t, tr, "AT+S"); err == nil {
		t.Fatal("exchange on an unplugged line succeeded")
	}
	if reply, err := exchange(t, tr, "AT+S"); err != nil || !strings.HasPrefix(reply, "S,") {
		t.Fatalf("after reopening: %q, %v", reply, err)
	}
	if robot.openCount() != 2 {
		t.Errorf("port opened %d times, want 2", robot.openCount())
	}
}

func TestLineTransportErrors(t *testing.T) {
	t.Run("port cannot be opened", func(t *testing.T) {
		tr := link.NewLineTransport(func() (io.ReadWriteCloser, error) { return nil, errors.New("no such port") }, time.Second)
		if _, err := exchange(t, tr, "AT+S"); err == nil || !strings.Contains(err.Error(), "no such port") {
			t.Errorf("err = %v", err)
		}
	})
	t.Run("request without checksum", func(t *testing.T) {
		tr := link.NewLineTransport((&serialRobot{sim: newSim(t)}).open, time.Second)
		if _, err := tr.Exchange(context.Background(), "AT+S"); !errors.Is(err, protocol.ErrMalformed) {
			t.Errorf("err = %v, want ErrMalformed", err)
		}
	})
	t.Run("cancelled", func(t *testing.T) {
		tr := link.NewLineTransport((&serialRobot{sim: newSim(t), mute: true}).open, time.Second)
		defer func() { _ = tr.Close() }()
		ctx, cancel := context.WithTimeout(context.Background(), 20*time.Millisecond)
		defer cancel()
		if _, err := tr.Exchange(ctx, protocol.Frame("AT+S")); !errors.Is(err, context.DeadlineExceeded) {
			t.Errorf("err = %v, want deadline exceeded", err)
		}
	})
	t.Run("write fails", func(t *testing.T) {
		tr := link.NewLineTransport(func() (io.ReadWriteCloser, error) {
			ours, theirs := net.Pipe()
			_ = theirs.Close()
			return ours, nil
		}, time.Second)
		if _, err := tr.Exchange(context.Background(), protocol.Frame("AT+S")); err == nil {
			t.Error("want write error")
		}
	})
}

func TestPollerOverSerialLine(t *testing.T) {
	robot := &serialRobot{sim: newSim(t), noise: []string{"LOOP: 12ms"}}
	tr := link.NewLineTransport(robot.open, time.Second)
	defer func() { _ = tr.Close() }()
	p := link.NewPoller(tr, fastPoll())
	rec := &recorder{}
	run(t, p, rec)

	rec.waitFor(t, "states over the serial line", func(r *recorder) bool { return len(r.states) >= 3 && r.obstacles >= 1 })
	if reply, err := p.Send(context.Background(), protocol.Dock().Encode()); err != nil || reply != "C" {
		t.Errorf("Send = %q, %v", reply, err)
	}
}
