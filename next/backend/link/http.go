package link

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// HTTPTimeout is how long one request to the robot may take (legacy value).
const HTTPTimeout = 6 * time.Second

// maxReplyBytes bounds a robot reply; the longest (AT+S2 with many
// obstacles) stays far below.
const maxReplyBytes = 64 << 10

// HTTPTransport talks to the robot's built-in web server: one POST per
// request line, the reply line is the response body.
type HTTPTransport struct {
	URL    string
	Client *http.Client
}

// NewHTTPTransport returns a transport for the robot at url, e.g. "http://192.168.1.50".
func NewHTTPTransport(url string) *HTTPTransport {
	return &HTTPTransport{URL: url, Client: &http.Client{Timeout: HTTPTimeout}}
}

// Exchange implements Transport.
func (t *HTTPTransport) Exchange(ctx context.Context, line string) (string, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, t.URL, strings.NewReader(line+"\n"))
	if err != nil {
		return "", fmt.Errorf("http request: %w", err)
	}
	req.Header.Set("Content-Type", "text/plain")
	res, err := t.Client.Do(req)
	if err != nil {
		return "", fmt.Errorf("http: %w", err)
	}
	defer func() { _ = res.Body.Close() }()
	body, err := io.ReadAll(io.LimitReader(res.Body, maxReplyBytes))
	if err != nil {
		return "", fmt.Errorf("http read reply: %w", err)
	}
	if res.StatusCode != http.StatusOK {
		return "", fmt.Errorf("http: robot answered %s", res.Status)
	}
	reply := strings.TrimSpace(string(body))
	if reply == "" {
		// The firmware answers with an empty body when it rejects the line
		// (bad checksum, wrong encryption key).
		return "", fmt.Errorf("http: %w", ErrNoReply)
	}
	return reply, nil
}
