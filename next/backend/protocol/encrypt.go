package protocol

import "fmt"

// Printable ASCII range the firmware encrypts; other bytes pass unchanged.
const (
	printableMin = 32
	printableMax = 126
)

// Key derives the HTTP encryption key from the robot password and the
// challenge the robot sent in its AT+V reply.
func Key(password, challenge int) (int, error) {
	if challenge <= 0 {
		return 0, fmt.Errorf("%w: encryption challenge %d", ErrMalformed, challenge)
	}
	key := password % challenge
	if key < 1 || key > printableMax-printableMin {
		return 0, fmt.Errorf("%w: encryption key %d out of range 1..94, check the password", ErrMalformed, key)
	}
	return key, nil
}

// Encrypt shifts every printable character of a framed request by key,
// wrapping around within the printable range. AT+V must never be encrypted.
func Encrypt(framed string, key int) string {
	return shift(framed, key)
}

// Decrypt reverses Encrypt. The robot does this; the simulator needs it too.
func Decrypt(encrypted string, key int) string {
	return shift(encrypted, -key)
}

func shift(s string, by int) string {
	const span = printableMax - printableMin + 1
	b := []byte(s)
	for i, c := range b {
		if c < printableMin || c > printableMax {
			continue
		}
		code := (int(c)-printableMin+by)%span + span
		b[i] = byte(code%span + printableMin)
	}
	return string(b)
}
