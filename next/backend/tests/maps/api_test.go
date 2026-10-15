package maps_test

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"net/http/httptest"
	"reflect"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/maps"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

type fakeUploader struct {
	got []protocol.Map
	err error
}

func (f *fakeUploader) UploadMap(_ context.Context, m protocol.Map) error {
	f.got = append(f.got, m)
	return f.err
}

func call(t *testing.T, h http.Handler, method, path, body string) *httptest.ResponseRecorder {
	t.Helper()
	rec := httptest.NewRecorder()
	h.ServeHTTP(rec, httptest.NewRequest(method, path, strings.NewReader(body)))
	return rec
}

func toJSON(t *testing.T, v any) string {
	t.Helper()
	b, err := json.Marshal(v)
	if err != nil {
		t.Fatal(err)
	}
	return string(b)
}

func TestAPICreateGetListUpdateDelete(t *testing.T) {
	f := newStore(t)
	h := f.store.Handler(&fakeUploader{})

	rec := call(t, h, http.MethodPost, "/api/maps", `{"name": "Garden", "perimeter": [{"x":0,"y":0},{"x":1,"y":0},{"x":1,"y":1}]}`)
	if rec.Code != http.StatusCreated {
		t.Fatalf("create: %d %s", rec.Code, rec.Body)
	}
	var created maps.Map
	_ = json.Unmarshal(rec.Body.Bytes(), &created)
	if created.ID != "m1" || !strings.Contains(rec.Body.String(), `"dock":[]`) {
		t.Errorf("created = %s", rec.Body)
	}

	rec = call(t, h, http.MethodGet, "/api/maps/m1", "")
	if rec.Code != http.StatusOK || !strings.Contains(rec.Body.String(), `"name":"Garden"`) {
		t.Errorf("get: %d %s", rec.Code, rec.Body)
	}

	created.Name = "Renamed"
	created.ID = "ignored, the path counts"
	if rec = call(t, h, http.MethodPut, "/api/maps/m1", toJSON(t, created)); rec.Code != http.StatusOK {
		t.Fatalf("update: %d %s", rec.Code, rec.Body)
	}

	rec = call(t, h, http.MethodGet, "/api/maps", "")
	var list maps.ListJSON
	_ = json.Unmarshal(rec.Body.Bytes(), &list)
	if len(list.Maps) != 1 || list.Maps[0].Name != "Renamed" || list.Maps[0].ID != "m1" || list.ActiveID != "" {
		t.Errorf("list = %s", rec.Body)
	}

	if rec = call(t, h, http.MethodDelete, "/api/maps/m1", ""); rec.Code != http.StatusNoContent {
		t.Errorf("delete: %d %s", rec.Code, rec.Body)
	}
	if rec = call(t, h, http.MethodGet, "/api/maps", ""); rec.Body.String() != `{"activeId":"","maps":[]}`+"\n" {
		t.Errorf("empty list = %s, want [] not null", rec.Body)
	}
}

func TestAPIActive(t *testing.T) {
	f := newStore(t)
	h := f.store.Handler(&fakeUploader{})
	m, _ := f.store.Create(garden("Garden"))
	if rec := call(t, h, http.MethodPut, "/api/maps/active", `{"id": "`+m.ID+`"}`); rec.Code != http.StatusNoContent {
		t.Fatalf("activate: %d %s", rec.Code, rec.Body)
	}
	if f.store.ActiveID() != m.ID {
		t.Error("not active")
	}
	if rec := call(t, h, http.MethodPut, "/api/maps/active", `{"id": ""}`); rec.Code != http.StatusNoContent || f.store.ActiveID() != "" {
		t.Errorf("deactivate: %d, active %q", rec.Code, f.store.ActiveID())
	}
	if rec := call(t, h, http.MethodPut, "/api/maps/active", `{}`); rec.Code != http.StatusBadRequest {
		t.Errorf("missing id: %d", rec.Code)
	}
	if rec := call(t, h, http.MethodPut, "/api/maps/active", `{"id": "nope"}`); rec.Code != http.StatusNotFound {
		t.Errorf("unknown id: %d", rec.Code)
	}
}

func TestAPIErrors(t *testing.T) {
	tests := []struct {
		method, path, body string
		want               int
	}{
		{http.MethodGet, "/api/maps/nope", "", http.StatusNotFound},
		{http.MethodPut, "/api/maps/nope", toJSON(t, garden("X")), http.StatusNotFound},
		{http.MethodDelete, "/api/maps/nope", "", http.StatusNotFound},
		{http.MethodPost, "/api/maps/nope/upload", "", http.StatusNotFound},
		{http.MethodPost, "/api/maps", `{"name": "Garden", "perimeter": []}`, http.StatusBadRequest},
		{http.MethodPost, "/api/maps", toJSON(t, garden("taken")), http.StatusConflict},
		{http.MethodPost, "/api/maps", `{"name": "X", "color": "red"}`, http.StatusBadRequest},
		{http.MethodPost, "/api/maps", `{`, http.StatusBadRequest},
		{http.MethodPut, "/api/maps/m1", `{`, http.StatusBadRequest},
		{http.MethodPut, "/api/maps/active", `{`, http.StatusBadRequest},
	}
	for _, tt := range tests {
		t.Run(fmt.Sprintf("%s %s %s", tt.method, tt.path, tt.body), func(t *testing.T) {
			f := newStore(t)
			_, _ = f.store.Create(garden("taken"))
			rec := call(t, f.store.Handler(&fakeUploader{}), tt.method, tt.path, tt.body)
			if rec.Code != tt.want || !strings.Contains(rec.Body.String(), `"error"`) {
				t.Errorf("got %d %s, want %d with error", rec.Code, rec.Body, tt.want)
			}
		})
	}
}

func TestAPIUpload(t *testing.T) {
	f := newStore(t)
	up := &fakeUploader{}
	m, _ := f.store.Create(garden("Garden"))
	rec := call(t, f.store.Handler(up), http.MethodPost, "/api/maps/"+m.ID+"/upload", "")
	if rec.Code != http.StatusNoContent {
		t.Fatalf("upload: %d %s", rec.Code, rec.Body)
	}
	if len(up.got) != 1 || !reflect.DeepEqual(up.got[0], m.Robot(nil)) {
		t.Errorf("uploaded %+v, want %+v", up.got, m.Robot(nil))
	}
	if f.store.ActiveID() != m.ID {
		t.Error("uploaded map is not active")
	}
}

func TestAPIUploadErrors(t *testing.T) {
	tests := []struct {
		err  error
		want int
	}{
		{link.ErrOffline, http.StatusServiceUnavailable},
		{fmt.Errorf("upload map: %w", robot.ErrBusy), http.StatusConflict},
		{robot.ErrMapCRCMismatch, http.StatusBadGateway},
		{context.DeadlineExceeded, http.StatusGatewayTimeout},
		{errors.New("broken"), http.StatusBadGateway},
	}
	for _, tt := range tests {
		t.Run(tt.err.Error(), func(t *testing.T) {
			f := newStore(t)
			m, _ := f.store.Create(garden("Garden"))
			rec := call(t, f.store.Handler(&fakeUploader{err: tt.err}), http.MethodPost, "/api/maps/"+m.ID+"/upload", "")
			if rec.Code != tt.want {
				t.Errorf("status %d, want %d", rec.Code, tt.want)
			}
			if f.store.ActiveID() != "" {
				t.Error("a failed upload must not change the active map")
			}
		})
	}
}
