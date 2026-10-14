// Package protocol encodes and decodes Sunray AT messages. It performs no I/O.
//
// A message on the wire is "PAYLOAD,0xCS" where CS is the sum of all payload
// bytes modulo 256. Requests start with "AT+", replies with the command
// letter(s), e.g. "AT+S" is answered by "S,...". The firmware reference is
// sunray/comm.cpp in github.com/Ardumower/Sunray.
package protocol

import (
	"errors"
	"fmt"
	"strconv"
	"strings"
)

var (
	// ErrChecksum means the received checksum does not match the payload.
	ErrChecksum = errors.New("checksum mismatch")
	// ErrMalformed means a message does not follow the expected format.
	ErrMalformed = errors.New("malformed message")
)

// Checksum returns the Sunray checksum of payload.
func Checksum(payload string) byte {
	var sum byte
	for i := 0; i < len(payload); i++ {
		sum += payload[i]
	}
	return sum
}

// Frame appends the checksum to payload. It is accepted by every channel:
// HTTP verifies it, UART/console strips it.
func Frame(payload string) string {
	return fmt.Sprintf("%s,0x%02x", payload, Checksum(payload))
}

// Unframe verifies the checksum of a received line and returns the payload
// without checksum and line ending.
func Unframe(line string) (string, error) {
	line = strings.TrimRight(line, "\r\n")
	idx := strings.LastIndexByte(line, ',')
	if idx < 1 {
		return "", fmt.Errorf("%w: no checksum in %q", ErrMalformed, line)
	}
	payload, cs := line[:idx], line[idx+1:]
	want, err := strconv.ParseUint(strings.TrimPrefix(strings.ToLower(cs), "0x"), 16, 8)
	if err != nil {
		return "", fmt.Errorf("%w: invalid checksum %q", ErrMalformed, cs)
	}
	if got := Checksum(payload); got != byte(want) {
		return "", fmt.Errorf("%w: got 0x%02x, message says 0x%02x", ErrChecksum, got, want)
	}
	return payload, nil
}

// ReplyMatches reports whether reply is the answer to request, e.g. "C" or
// "C,..." answers "AT+C,...". request and reply are payloads without checksum.
func ReplyMatches(request, reply string) bool {
	cmd, ok := strings.CutPrefix(request, "AT+")
	if !ok {
		return false
	}
	return firstField(cmd) == firstField(reply)
}

func firstField(s string) string {
	name, _, _ := strings.Cut(s, ",")
	return name
}
