package protocol_test

import (
	"fmt"
	"strings"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Expected strings are what legacy CaSSAndRA sends (sunraycommstack.py), so
// the robot sees exactly the same commands.
func TestControlMatchesLegacy(t *testing.T) {
	tests := []struct {
		name string
		cmd  protocol.Control
		want string
	}{
		{"stop", protocol.Stop(), "AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"dock", protocol.Dock(), "AT+C,0,4,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"mow", protocol.Mow(0.25, 60, false), "AT+C,1,1,0.25,60,0,-1,-1,-1,-1,-1,1"},
		{"mow with finish and restart", protocol.Mow(0.3, 120, true), "AT+C,1,1,0.3,120,1,-1,-1,-1,-1,-1,1"},
		{"goto", protocol.Goto(0.3, 60), "AT+C,0,1,0.3,60,0,-1,-1,-1,-1,-1,0"},
		{"mow motor on", protocol.MowMotor(true), "AT+C,1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"mow motor off", protocol.MowMotor(false), "AT+C,0,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"change speed", protocol.Speed(0.35), "AT+C,-1,-1,0.35,-1,-1,-1,-1,-1,-1,-1,-1"},
		{"skip next point", protocol.SkipNextPoint(), "AT+C,-1,-1,-1,-1,-1,-1,1,-1,-1,-1,-1"},
		{"skip to progress", protocol.SkipToProgress(0.42), "AT+C,-1,-1,-1,-1,-1,0.42,-1,-1,-1,-1,-1"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := tt.cmd.Encode(); got != tt.want {
				t.Errorf("Encode() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestEmptyControlChangesNothing(t *testing.T) {
	want := "AT+C,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1"
	if got := (protocol.Control{}).Encode(); got != want {
		t.Errorf("Control{}.Encode() = %q, want %q", got, want)
	}
}

func TestControlAllFieldsInWireOrder(t *testing.T) {
	c := protocol.Control{
		MowMotor:         protocol.Some(true),
		Op:               protocol.Some(protocol.OpDock),
		SpeedMps:         protocol.Some(0.5),
		FixTimeoutSec:    protocol.Some(30),
		FinishAndRestart: protocol.Some(true),
		MowProgress:      protocol.Some(0.5),
		SkipNextPoint:    true,
		Sonar:            protocol.Some(false),
		MowPWM:           protocol.Some(200),
		MowHeightMM:      protocol.Some(45),
		DockAfterFinish:  protocol.Some(false),
	}
	want := "AT+C,1,4,0.5,30,1,0.5,1,0,200,45,0"
	if got := c.Encode(); got != want {
		t.Errorf("Encode() = %q, want %q", got, want)
	}
}

func TestOpString(t *testing.T) {
	want := map[protocol.Op]string{
		protocol.OpIdle: "idle", protocol.OpMow: "mow", protocol.OpCharge: "charge",
		protocol.OpError: "error", protocol.OpDock: "dock", protocol.Op(9): "op(9)",
	}
	for op, name := range want {
		if got := op.String(); got != name {
			t.Errorf("Op(%d).String() = %q, want %q", int(op), got, name)
		}
	}
}

func TestSimpleRequests(t *testing.T) {
	tests := []struct{ got, want string }{
		{protocol.RequestVersion, "AT+V"},
		{protocol.RequestState, "AT+S"},
		{protocol.RequestStats, "AT+T"},
		{protocol.RequestObstacles, "AT+S2"},
		{protocol.Reboot, "AT+Y"},
		{protocol.RebootGPS, "AT+Y2"},
		{protocol.Shutdown, "AT+Y3"},
		{protocol.Move(0.2, -0.5), "AT+M,0.2,-0.5"},
		{protocol.Move(0, 0), "AT+M,0,0"},
		{protocol.PositionMode(false, 0, 0), "AT+P,0,0,0"},
		{protocol.PositionMode(true, 13.40495, 52.52001), "AT+P,1,13.40495,52.52001"},
	}
	for _, tt := range tests {
		if tt.got != tt.want {
			t.Errorf("got %q, want %q", tt.got, tt.want)
		}
	}
}

func pts(coords ...float64) []geo.Point {
	p := make([]geo.Point, len(coords)/2)
	for i := range p {
		p[i] = geo.Point{X: coords[2*i], Y: coords[2*i+1]}
	}
	return p
}

func TestMapUpload(t *testing.T) {
	m := protocol.Map{
		Perimeter:  pts(0, 0, 10, 0, 10, 10, 0, 10),
		Exclusions: [][]geo.Point{pts(2, 2, 3, 2, 3, 3), pts(6, 6, 7, 6, 7, 7, 6, 7)},
		Dock:       pts(1, 1, 1, 2),
		Way:        pts(1.234, 5.678, -0.004, 9.996),
	}
	want := []string{
		"AT+W,0,0,0,10,0,10,10,0,10,2,2,3,2,3,3,6,6,7,6,7,7,6,7,1,1,1,2,1.23,5.68,0,10",
		"AT+N,4,7,2,2,0",
		"AT+X,0,3,4",
	}
	assertMessages(t, protocol.MapUpload(m), want)
}

func TestMapUploadWithoutExclusionsAndDock(t *testing.T) {
	m := protocol.Map{Perimeter: pts(0, 0, 5, 0, 5, 5), Way: pts(1, 1)}
	want := []string{
		"AT+W,0,0,0,5,0,5,5,1,1",
		"AT+N,3,0,0,1,0",
		"AT+X,0",
	}
	assertMessages(t, protocol.MapUpload(m), want)
}

func TestMapUploadSplitsIntoPacketsOf30Points(t *testing.T) {
	way := make([]geo.Point, 65)
	for i := range way {
		way[i] = geo.Point{X: float64(i), Y: 0}
	}
	msgs := protocol.MapUpload(protocol.Map{Way: way})

	if len(msgs) != 5 {
		t.Fatalf("got %d messages, want 3x AT+W + AT+N + AT+X: %q", len(msgs), msgs)
	}
	for i, start := range []int{0, 30, 60} {
		prefix := fmt.Sprintf("AT+W,%d,%d,0,", start, start)
		if !strings.HasPrefix(msgs[i], prefix) {
			t.Errorf("message %d = %q, want prefix %q", i, msgs[i], prefix)
		}
	}
	if n := strings.Count(msgs[1], ","); n != 1+2*30 {
		t.Errorf("second packet has %d commas, want 61 (start + 30 points)", n)
	}
	if !strings.HasSuffix(msgs[2], ",64,0") {
		t.Errorf("last packet = %q, want it to end with the last point", msgs[2])
	}
	if msgs[3] != "AT+N,0,0,0,65,0" {
		t.Errorf("count message = %q", msgs[3])
	}
}

func TestMapUploadEmpty(t *testing.T) {
	assertMessages(t, protocol.MapUpload(protocol.Map{}), []string{"AT+N,0,0,0,0,0", "AT+X,0"})
}

func assertMessages(t *testing.T, got, want []string) {
	t.Helper()
	if len(got) != len(want) {
		t.Fatalf("got %d messages %q, want %d %q", len(got), got, len(want), want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("message %d:\n got %q\nwant %q", i, got[i], want[i])
		}
	}
}
