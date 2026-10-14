package link_test

import (
	"context"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/tests/testkit"
)

func TestHTTPTransportExchange(t *testing.T) {
	srv := testkit.RobotHTTPServer(t, newSim(t))
	tr := link.NewHTTPTransport(srv.URL)

	line, err := tr.Exchange(context.Background(), protocol.Frame("AT+V"))
	if err != nil {
		t.Fatal(err)
	}
	if reply, err := protocol.Unframe(line); err != nil || !strings.HasPrefix(reply, "V,Sunray") {
		t.Errorf("reply = %q, %v", line, err)
	}
}

func TestHTTPTransportErrors(t *testing.T) {
	sim := newSim(t)
	tests := []struct {
		name    string
		handler http.HandlerFunc
		want    error
	}{
		{"rejected line", func(http.ResponseWriter, *http.Request) {}, link.ErrNoReply},
		{"server error", func(w http.ResponseWriter, _ *http.Request) {
			http.Error(w, "boom", http.StatusInternalServerError)
		}, nil},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			srv := httptest.NewServer(tt.handler)
			defer srv.Close()
			_, err := link.NewHTTPTransport(srv.URL).Exchange(context.Background(), protocol.Frame("AT+S"))
			if err == nil || (tt.want != nil && !errors.Is(err, tt.want)) {
				t.Errorf("err = %v, want %v", err, tt.want)
			}
		})
	}

	t.Run("robot unreachable", func(t *testing.T) {
		srv := testkit.RobotHTTPServer(t, sim)
		url := srv.URL
		srv.Close()
		if _, err := link.NewHTTPTransport(url).Exchange(context.Background(), protocol.Frame("AT+S")); err == nil {
			t.Error("want error for a closed server")
		}
	})

	t.Run("timeout", func(t *testing.T) {
		// The server only notices the client hanging up after the body is read.
		srv := httptest.NewServer(http.HandlerFunc(func(_ http.ResponseWriter, r *http.Request) {
			_, _ = io.ReadAll(r.Body)
			select {
			case <-r.Context().Done():
			case <-time.After(2 * time.Second):
			}
		}))
		defer srv.Close()
		tr := link.NewHTTPTransport(srv.URL)
		tr.Client.Timeout = 20 * time.Millisecond
		if _, err := tr.Exchange(context.Background(), protocol.Frame("AT+S")); err == nil {
			t.Error("want timeout error")
		}
	})

	t.Run("invalid URL", func(t *testing.T) {
		if _, err := link.NewHTTPTransport("http://bad host").Exchange(context.Background(), "x"); err == nil {
			t.Error("want error for an invalid URL")
		}
	})
}

func TestPollerOverHTTPWithEncryption(t *testing.T) {
	cfg := link.DefaultSimConfig()
	cfg.Password = 4711
	srv := testkit.RobotHTTPServer(t, link.NewSim(cfg))

	pc := fastPoll()
	pc.Encrypt, pc.Password = true, 4711
	p := link.NewPoller(link.NewHTTPTransport(srv.URL), pc)
	rec := &recorder{}
	run(t, p, rec)

	rec.waitFor(t, "states over encrypted HTTP", func(r *recorder) bool { return len(r.states) >= 2 && r.stats >= 1 })
	if reply, err := p.Send(context.Background(), protocol.Dock().Encode()); err != nil || reply != "C" {
		t.Errorf("Send = %q, %v", reply, err)
	}
}

func TestDefaultHTTPTimeoutMatchesLegacy(t *testing.T) {
	if link.HTTPTimeout != 6*time.Second || link.NewHTTPTransport("http://x").Client.Timeout != 6*time.Second {
		t.Errorf("HTTP timeout = %v", link.HTTPTimeout)
	}
}
