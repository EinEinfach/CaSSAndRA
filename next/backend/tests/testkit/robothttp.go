package testkit

import (
	"context"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

// Exchanger answers one request line (link.Sim implements it).
type Exchanger interface {
	Exchange(ctx context.Context, line string) (string, error)
}

// RobotHTTPServer answers like the Sunray web server with robot behind it.
// The firmware sends an empty body for lines it rejects.
func RobotHTTPServer(t testing.TB, robot Exchanger) *httptest.Server {
	t.Helper()
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "post only", http.StatusMethodNotAllowed)
			return
		}
		body, _ := io.ReadAll(r.Body)
		reply, err := robot.Exchange(r.Context(), string(body))
		if err != nil {
			return
		}
		_, _ = io.WriteString(w, reply)
	}))
	t.Cleanup(srv.Close)
	return srv
}
