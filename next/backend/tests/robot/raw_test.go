package robot_test

import (
	"context"
	"errors"
	"net/http"
	"reflect"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/link"
	"github.com/EinEinfach/CaSSAndRA/next/backend/robot"
)

func TestSendRawSendsOnceAndReturnsTheReply(t *testing.T) {
	f := newFixture(t)
	f.sender.replies["AT+V"] = "V,Ardumower Sunray,1.0.331,1,78"
	reply, err := f.robot.SendRaw(context.Background(), "  AT+V  ")
	if err != nil {
		t.Fatal(err)
	}
	if reply != "V,Ardumower Sunray,1.0.331,1,78" {
		t.Errorf("reply = %q", reply)
	}
	if got := f.sender.payloads(); !reflect.DeepEqual(got, []string{"AT+V"}) {
		t.Errorf("sent %q, want AT+V once, without spaces (the link adds the checksum)", got)
	}
}

func TestSendRawIsNeverRepeated(t *testing.T) {
	f := newFixture(t)
	f.sender.fail["AT+M"] = 1
	if _, err := f.robot.SendRaw(context.Background(), "AT+M,0.2,0"); !errors.Is(err, errLinkDown) {
		t.Errorf("err = %v, want the link error", err)
	}
	if got := f.sender.payloads(); len(got) != 1 {
		t.Errorf("sent %q, want one try", got)
	}
}

func TestSendRawRejectsWhatIsNoCommand(t *testing.T) {
	for _, line := range []string{"", "AT+", "V", "at+v", "AT+V\r\nAT+Y", "AT+Ö", "AT+" + strings.Repeat("1", 200)} {
		f := newFixture(t)
		if _, err := f.robot.SendRaw(context.Background(), line); !errors.Is(err, robot.ErrInvalidCommand) {
			t.Errorf("%q: err = %v, want ErrInvalidCommand", line, err)
		}
		if got := f.sender.payloads(); len(got) != 0 {
			t.Errorf("%q: sent %q", line, got)
		}
	}
}

func TestAPIRaw(t *testing.T) {
	tests := []struct {
		name, body string
		fail       bool
		want       int
		wantBody   string
	}{
		{"reply", `{"line":"AT+S"}`, false, http.StatusOK, `{"reply":"S"}`},
		{"no line", `{}`, false, http.StatusBadRequest, ""},
		{"not AT+", `{"line":"reboot"}`, false, http.StatusBadRequest, ""},
		{"link down", `{"line":"AT+S"}`, true, http.StatusBadGateway, ""},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			f := newFixture(t)
			if tt.fail {
				f.sender.fail["AT+S"] = 1
			}
			rec := call(t, f.robot.Handler(), http.MethodPost, "/api/robot/raw", tt.body)
			if rec.Code != tt.want {
				t.Fatalf("status = %d (%s), want %d", rec.Code, rec.Body, tt.want)
			}
			if tt.wantBody != "" && strings.TrimSpace(rec.Body.String()) != tt.wantBody {
				t.Errorf("body = %s, want %s", rec.Body, tt.wantBody)
			}
		})
	}
	if robot.ErrorStatus(link.ErrOffline) != http.StatusServiceUnavailable {
		t.Error("offline is not 503")
	}
}
