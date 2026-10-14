package protocol_test

import (
	"errors"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

func TestChecksum(t *testing.T) {
	tests := []struct {
		payload string
		want    byte
	}{
		{"", 0},
		{"AT+S", 0x13},
		{"AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1", 0x95},
		{"C", 0x43},
	}
	for _, tt := range tests {
		if got := protocol.Checksum(tt.payload); got != tt.want {
			t.Errorf("Checksum(%q) = 0x%02x, want 0x%02x", tt.payload, got, tt.want)
		}
	}
}

func TestFrame(t *testing.T) {
	tests := []struct{ payload, want string }{
		{"AT+S", "AT+S,0x13"},
		{"AT+M,0.5,-0.3", "AT+M,0.5,-0.3,0xb6"},
		// Firmware pads to two digits; legacy CaSSAndRA did not. Both parse.
		{"AT+W,0,1.5,-2.25,3,4", "AT+W,0,1.5,-2.25,3,4,0x12"},
	}
	for _, tt := range tests {
		if got := protocol.Frame(tt.payload); got != tt.want {
			t.Errorf("Frame(%q) = %q, want %q", tt.payload, got, tt.want)
		}
	}
}

func TestUnframe(t *testing.T) {
	tests := []struct {
		name    string
		line    string
		want    string
		wantErr error
	}{
		{"robot reply with CRLF", "C,0x43\r\n", "C", nil},
		{"without line ending", "C,0x43", "C", nil},
		{"uppercase hex", "C,0X43", "C", nil},
		{"single digit as sent by legacy", "AT+W,0,1.5,-2.25,3,4,0x12", "AT+W,0,1.5,-2.25,3,4", nil},
		{"payload with fields", "W,30,0xe6\r\n", "W,30", nil},
		{"round trip", protocol.Frame("S2,0"), "S2,0", nil},
		{"wrong checksum", "C,0x44\r\n", "", protocol.ErrChecksum},
		{"no checksum", "C\r\n", "", protocol.ErrMalformed},
		{"empty", "", "", protocol.ErrMalformed},
		{"checksum not hex", "C,0xzz", "", protocol.ErrMalformed},
		{"checksum too large", "C,0x143", "", protocol.ErrMalformed},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got, err := protocol.Unframe(tt.line)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("err = %v, want %v", err, tt.wantErr)
			}
			if got != tt.want {
				t.Errorf("payload = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestGoldenRepliesHaveValidChecksums(t *testing.T) {
	for _, name := range []string{
		"version_current", "version_old", "state_mowing", "state_charging",
		"state_charging_negative_board_current", "state_idle_gps_invalid",
		"state_fw_1_0_300", "state_fw_1_0_250", "stats_current", "stats_fw_25_fields",
		"stats_fw_24_fields", "obstacles_none", "obstacles_two", "ack_control",
		"ack_waypoints", "ack_waycount", "ack_exclusions",
	} {
		if _, err := protocol.Unframe(golden(t, name)); err != nil {
			t.Errorf("%s: %v", name, err)
		}
	}
}

func TestReplyMatches(t *testing.T) {
	tests := []struct {
		request, reply string
		want           bool
	}{
		{"AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1", "C", true},
		{"AT+W,0,1,2", "W,1", true},
		{"AT+S", "S,27.5,1,2", true},
		{"AT+S2", "S2,0", true},
		{"AT+S2", "S,27.5", false},
		{"AT+S", "S2,0", false},
		{"AT+Y3", "Y3", true},
		{"AT+Y3", "Y", false},
		{"AT+C,1", "M", false},
		{"C", "C", false},
	}
	for _, tt := range tests {
		if got := protocol.ReplyMatches(tt.request, tt.reply); got != tt.want {
			t.Errorf("ReplyMatches(%q, %q) = %v, want %v", tt.request, tt.reply, got, tt.want)
		}
	}
}
