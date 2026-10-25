package mqttapi_test

import (
	"encoding/json"
	"math"
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/mqttapi"
)

type mqttFloat = mqttapi.Float

// Python's json module writes every float with a decimal point; Dart reads
// a number without one as int, which does not fit the app's double fields.
func TestFloatsAreWrittenLikePython(t *testing.T) {
	tests := []struct {
		in   float64
		want string
	}{
		{0, "0.0"}, {27, "27.0"}, {-1, "-1.0"}, {27.15, "27.15"}, {0.1, "0.1"},
		{1234567, "1234567.0"}, {math.NaN(), "0.0"}, {math.Inf(1), "0.0"},
	}
	for _, tt := range tests {
		b, err := json.Marshal(mqttapi.Float(tt.in))
		if err != nil || string(b) != tt.want {
			t.Errorf("Float(%v) = %s (%v), want %s", tt.in, b, err, tt.want)
		}
	}
}
