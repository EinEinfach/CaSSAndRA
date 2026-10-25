package mqttapi

import (
	"math"
	"strconv"
	"strings"
)

// Float is a number written the way Python's json module writes a float:
// always with a decimal point (27.0, not 27). The native app is written in
// Dart, where a JSON 27 is an int and does not fit a double field: the whole
// message would be dropped.
type Float float64

// MarshalJSON implements json.Marshaler. NaN and infinity become 0.0.
func (f Float) MarshalJSON() ([]byte, error) {
	v := float64(f)
	if math.IsNaN(v) || math.IsInf(v, 0) {
		v = 0
	}
	s := strconv.FormatFloat(v, 'f', -1, 64)
	if !strings.Contains(s, ".") {
		s += ".0"
	}
	return []byte(s), nil
}

// round2 rounds to two decimals, like the legacy payloads.
func round2(v float64) Float {
	return Float(math.Round(v*100) / 100)
}

// Point is [x, y] as in the legacy GeoJSON.
type Point [2]Float

// FloatOrNil is a Float that is null when unknown.
type FloatOrNil = *Float

func floatPtr(v float64) *Float {
	f := Float(v)
	return &f
}
