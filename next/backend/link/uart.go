package link

import (
	"bufio"
	"context"
	"fmt"
	"io"
	"sync"
	"time"

	"go.bug.st/serial"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// UARTReplyTimeout is how long to wait for the answer to one request.
const UARTReplyTimeout = 3 * time.Second

// LineTransport talks to the robot over a line based byte stream, such as
// the serial console. The firmware also prints log lines there, so lines
// are skipped until the reply to the request arrives.
type LineTransport struct {
	open         func() (io.ReadWriteCloser, error)
	replyTimeout time.Duration

	mu      sync.Mutex // one exchange at a time; guards conn
	conn    io.ReadWriteCloser
	lines   chan string
	readErr chan error
}

// NewUARTTransport opens the serial port lazily on the first exchange and
// reopens it after errors.
func NewUARTTransport(port string, baud int) *LineTransport {
	return NewLineTransport(func() (io.ReadWriteCloser, error) {
		return serial.Open(port, &serial.Mode{BaudRate: baud})
	}, UARTReplyTimeout)
}

// NewLineTransport returns a transport over connections from open.
func NewLineTransport(open func() (io.ReadWriteCloser, error), replyTimeout time.Duration) *LineTransport {
	return &LineTransport{open: open, replyTimeout: replyTimeout}
}

// Exchange implements Transport.
func (t *LineTransport) Exchange(ctx context.Context, line string) (string, error) {
	request, err := protocol.Unframe(line)
	if err != nil {
		return "", fmt.Errorf("uart: request must be framed: %w", err)
	}

	t.mu.Lock()
	defer t.mu.Unlock()
	if err := t.connectLocked(); err != nil {
		return "", err
	}

	// Drop lines that arrived since the last exchange.
	for len(t.lines) > 0 {
		<-t.lines
	}
	if _, err := io.WriteString(t.conn, line+"\n"); err != nil {
		t.closeLocked()
		return "", fmt.Errorf("uart write: %w", err)
	}

	timeout := time.NewTimer(t.replyTimeout)
	defer timeout.Stop()
	for {
		select {
		case <-ctx.Done():
			return "", ctx.Err()
		case <-timeout.C:
			return "", fmt.Errorf("uart: %w within %v", ErrNoReply, t.replyTimeout)
		case err := <-t.readErr:
			t.closeLocked()
			return "", fmt.Errorf("uart read: %w", err)
		case l := <-t.lines:
			if reply, err := protocol.Unframe(l); err == nil && protocol.ReplyMatches(request, reply) {
				return l, nil
			}
			// console output or the answer to something else
		}
	}
}

// Close releases the port.
func (t *LineTransport) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.closeLocked()
	return nil
}

func (t *LineTransport) connectLocked() error {
	if t.conn != nil {
		return nil
	}
	conn, err := t.open()
	if err != nil {
		return fmt.Errorf("uart open: %w", err)
	}
	t.conn = conn
	t.lines = make(chan string, 256)
	t.readErr = make(chan error, 1)
	go read(conn, t.lines, t.readErr)
	return nil
}

func (t *LineTransport) closeLocked() {
	if t.conn != nil {
		_ = t.conn.Close() // ends the reader goroutine
		t.conn = nil
	}
}

// read forwards lines until the connection fails. Lines that do not fit
// the buffer are dropped rather than blocking the reader.
func read(r io.Reader, lines chan<- string, readErr chan<- error) {
	sc := bufio.NewScanner(r)
	for sc.Scan() {
		select {
		case lines <- sc.Text():
		default:
		}
	}
	err := sc.Err()
	if err == nil {
		err = io.EOF
	}
	readErr <- err
}
