package protocol_test

import (
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// Replies arrive over radio and serial lines. Whatever comes in, parsing must
// return an error instead of panicking. Run longer with:
// go test ./tests/protocol -fuzz FuzzParseReplies -fuzztime 30s
func FuzzParseReplies(f *testing.F) {
	for _, name := range []string{
		"version_current", "state_mowing", "state_fw_1_0_250", "stats_current",
		"obstacles_two", "obstacles_none", "ack_waypoints",
	} {
		f.Add(golden(f, name))
	}
	f.Add("S2,99999999,0.5")
	f.Add("S2,1,0.5,0.5,1,99999999999")
	f.Add(",,,,0x00")
	f.Add(`{"battery_voltage":1,"position":{"x":1,"y":2},"job":1}`)
	f.Fuzz(func(_ *testing.T, line string) {
		p, err := protocol.Unframe(line)
		if err != nil {
			p = line // also feed unframed garbage to the parsers
		}
		_, _ = protocol.ParseVersion(p)
		_, _ = protocol.ParseState(p)
		_, _ = protocol.ParseStats(p)
		_, _ = protocol.ParseObstacles(p)
		_, _ = protocol.ParseWaypointAck(p)
		_ = protocol.ReplyMatches(p, p)
		_, _ = protocol.ParseBridgeState([]byte(line))
		_, _ = protocol.ParseBridgeStats([]byte(line))
		_, _ = protocol.ParseBridgeProps([]byte(line))
		_, _ = protocol.ParseBridgeOnline([]byte(line))
	})
}

func FuzzEncryptRoundTrip(f *testing.F) {
	f.Add("AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1,0x95", 37)
	f.Add("\x00\x7f\xff~ ", 94)
	f.Fuzz(func(t *testing.T, msg string, key int) {
		key = 1 + abs(key)%94
		if got := protocol.Decrypt(protocol.Encrypt(msg, key), key); got != msg {
			t.Fatalf("round trip with key %d: got %q, want %q", key, got, msg)
		}
	})
}

func abs(v int) int {
	if v < 0 {
		return -v
	}
	return v
}
