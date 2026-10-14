package protocol_test

import (
	"errors"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

func TestKey(t *testing.T) {
	tests := []struct {
		password, challenge, want int
		wantErr                   error
	}{
		{1234, 57, 37, nil},
		{4711, 100, 11, nil},
		{94, 100, 94, nil},
		{1, 100, 1, nil},
		{1200, 100, 0, protocol.ErrMalformed}, // key 0 would not encrypt
		{4711, 199, 0, protocol.ErrMalformed}, // key 134 is out of range
		{1234, 0, 0, protocol.ErrMalformed},
		{1234, -5, 0, protocol.ErrMalformed},
	}
	for _, tt := range tests {
		got, err := protocol.Key(tt.password, tt.challenge)
		if !errors.Is(err, tt.wantErr) {
			t.Errorf("Key(%d, %d) err = %v, want %v", tt.password, tt.challenge, err, tt.wantErr)
		}
		if got != tt.want {
			t.Errorf("Key(%d, %d) = %d, want %d", tt.password, tt.challenge, got, tt.want)
		}
	}
}

// Expected values come from the legacy CaSSAndRA implementation.
func TestEncryptMatchesLegacy(t *testing.T) {
	tests := []struct {
		framed string
		key    int
		want   string
	}{
		{"AT+S,0x13", 37, "fyPxQU>VX"},
		{"AT+C,0,0,-1,-1,-1,-1,-1,-1,-1,-1,-1,0x95", 37, "fyPhQUQUQRVQRVQRVQRVQRVQRVQRVQRVQRVQU>^Z"},
		{"AT+M,0.5,-0.3,0xb6", 11, "L_6X7;9@78;9>7;$mA"},
		{"AT+M,0.5,-0.3,0xb6", 94, "@S*L+/-4+,/-2+/wa5"},
		{"AT+W,0,1.5,-2.25,3,4,0x12", 11, "L_6b7;7<9@78=9=@7>7?7;$<="},
	}
	for _, tt := range tests {
		if got := protocol.Encrypt(tt.framed, tt.key); got != tt.want {
			t.Errorf("Encrypt(%q, %d) = %q, want %q", tt.framed, tt.key, got, tt.want)
		}
	}
}

func TestDecryptReversesEncrypt(t *testing.T) {
	msg := protocol.Frame("AT+W,0,1.5,-2.25,3,4") + "\n"
	for key := 1; key <= 94; key++ {
		enc := protocol.Encrypt(msg, key)
		if got := protocol.Decrypt(enc, key); got != msg {
			t.Fatalf("key %d: Decrypt(Encrypt(m)) = %q, want %q", key, got, msg)
		}
		for i := 0; i < len(enc); i++ {
			if c := enc[i]; c != '\n' && (c < 32 || c > 126) {
				t.Fatalf("key %d: encrypted byte %d = %d is not printable", key, i, c)
			}
		}
		if enc[len(enc)-1] != '\n' {
			t.Fatalf("key %d: line ending was encrypted", key)
		}
	}
}
