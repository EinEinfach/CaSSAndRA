package logs_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/logs"
)

func newLogger(size int) (*slog.Logger, *logs.Buffer, *bytes.Buffer) {
	var out bytes.Buffer
	buf := logs.NewBuffer(slog.NewTextHandler(&out, &slog.HandlerOptions{Level: slog.LevelInfo}), size)
	return slog.New(buf), buf, &out
}

func messages(entries []logs.Entry) []string {
	out := make([]string, len(entries))
	for i, e := range entries {
		out[i] = e.Message
	}
	return out
}

func TestBufferKeepsRecordsAndPassesThemOn(t *testing.T) {
	log, buf, out := newLogger(10)
	log.Debug("hidden")
	log.Info("command", "cmd", "mow")
	log.With("feature", "robot").WithGroup("link").Warn("offline", "after", "6s", "why", "no reply")
	log.Error("broken", slog.Group("map", "id", "m1", "name", ""))

	got := buf.Since(0, 0)
	want := []string{
		"command cmd=mow",
		`offline feature=robot link.after=6s link.why="no reply"`,
		`broken map.id=m1 map.name=""`,
	}
	if strings.Join(messages(got), "\n") != strings.Join(want, "\n") {
		t.Errorf("messages = %q, want %q", messages(got), want)
	}
	if got[0].Level != "INFO" || got[1].Level != "WARN" || got[2].Level != "ERROR" {
		t.Errorf("levels = %s %s %s", got[0].Level, got[1].Level, got[2].Level)
	}
	if got[0].Seq != 1 || got[2].Seq != 3 || got[0].Time.IsZero() {
		t.Errorf("entries = %+v", got)
	}
	if !strings.Contains(out.String(), "msg=command cmd=mow") || strings.Contains(out.String(), "hidden") {
		t.Errorf("passed on:\n%s", out)
	}
}

func TestBufferKeepsTheNewest(t *testing.T) {
	log, buf, _ := newLogger(3)
	for i := 1; i <= 5; i++ {
		log.Info(fmt.Sprint("m", i))
	}
	if got := messages(buf.Since(0, 0)); strings.Join(got, ",") != "m3,m4,m5" {
		t.Errorf("kept %v, want m3..m5", got)
	}
	if got := messages(buf.Since(4, 0)); strings.Join(got, ",") != "m5" {
		t.Errorf("since 4: %v, want m5", got)
	}
	if got := buf.Since(5, 0); got == nil || len(got) != 0 {
		t.Errorf("since the newest: %v, want an empty list", got)
	}
	if got := messages(buf.Since(0, 2)); strings.Join(got, ",") != "m4,m5" {
		t.Errorf("limit 2: %v, want the newest two", got)
	}
}

func TestBufferIsSafeForConcurrentUse(t *testing.T) {
	log, buf, _ := newLogger(50)
	var wg sync.WaitGroup
	for g := range 8 {
		wg.Go(func() {
			l := log.With("g", g)
			for range 100 {
				l.Info("x")
				buf.Since(0, 0)
			}
		})
	}
	wg.Wait()
	got := buf.Since(0, 0)
	if len(got) != 50 || got[49].Seq != 800 {
		t.Errorf("kept %d, last seq %d; want 50 and 800", len(got), got[len(got)-1].Seq)
	}
}

func TestAPI(t *testing.T) {
	log, buf, _ := newLogger(10)
	log.Info("one")
	log.Info("two")
	h := buf.Handler()
	get := func(path string) *httptest.ResponseRecorder {
		rec := httptest.NewRecorder()
		h.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, path, http.NoBody))
		return rec
	}
	var list logs.ListJSON
	if err := json.Unmarshal(get("/api/logs?after=1").Body.Bytes(), &list); err != nil {
		t.Fatal(err)
	}
	if strings.Join(messages(list.Entries), ",") != "two" {
		t.Errorf("after=1: %v", list.Entries)
	}
	if body := get("/api/logs?after=2").Body.String(); body != `{"entries":[]}`+"\n" {
		t.Errorf("nothing new = %s, want an empty list", body)
	}
	if !strings.Contains(get("/api/logs").Body.String(), `"one"`) {
		t.Error("without after: not all records")
	}
	for _, bad := range []string{"x", "-1"} {
		if rec := get("/api/logs?after=" + bad); rec.Code != http.StatusBadRequest {
			t.Errorf("after=%s: status %d, want 400", bad, rec.Code)
		}
	}
}
