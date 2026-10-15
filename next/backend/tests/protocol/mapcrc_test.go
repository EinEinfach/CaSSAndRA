package protocol_test

import (
	"testing"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
	"github.com/EinEinfach/CaSSAndRA/next/backend/protocol"
)

// crcMap uses coordinates that the Arduino firmware truncates to a
// different centimeter value (e.g. -40.94 -> -4093).
var crcMap = protocol.Map{
	Perimeter:  pts(0, 0, -40.94, 0.29, -40.85, -40.76, 12.5, -40.69, 327.67, -327.61),
	Exclusions: [][]geo.Point{pts(1.15, 2.3, -4.71, -36.98, 0.07, 0.57), pts(-40.67, -40.6, 10.01, -0.01, -40.51, 5)},
	Dock:       pts(-1, 3, 1, 3),
	Way:        pts(-4.71, -36.88, -40.94, -40.94),
}

// Expected values come from testdata/map_crc_reference.c, which runs the
// firmware's Point code on the same points (see the comment there):
//
//	cc -o crc testdata/map_crc_reference.c && printf '0 0\n-40.94 0.29\n...' | ./crc
func TestMapChecksum(t *testing.T) {
	tests := []struct {
		name string
		m    protocol.Map
		want protocol.MapCRC
	}{
		{"full map", crcMap, protocol.MapCRC{Arduino: -41214, Linux: -41218}},
		{"without dock and way", protocol.Map{Perimeter: crcMap.Perimeter, Exclusions: crcMap.Exclusions},
			protocol.MapCRC{Arduino: -29469, Linux: -29472}},
		{"empty", protocol.Map{}, protocol.MapCRC{}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := protocol.MapChecksum(tt.m); got != tt.want {
				t.Errorf("got %+v, want %+v", got, tt.want)
			}
		})
	}
}

func TestMapChecksumUsesSentCoordinates(t *testing.T) {
	sent := protocol.Map{Perimeter: pts(-40.94, 0.29, 1.15, 2.3)}
	unrounded := protocol.Map{Perimeter: pts(-40.9449, 0.2851, 1.1450001, 2.30004)}
	if a, b := protocol.MapChecksum(sent), protocol.MapChecksum(unrounded); a != b {
		t.Errorf("unrounded map: %+v, want the CRC of what is sent %+v", b, a)
	}
}

func TestMapCRCMatches(t *testing.T) {
	crc := protocol.MapCRC{Arduino: -41214, Linux: -41218}
	for reported, want := range map[int64]bool{-41214: true, -41218: true, -41216: false, 0: false} {
		if got := crc.Matches(reported); got != want {
			t.Errorf("Matches(%d) = %v, want %v", reported, got, want)
		}
	}
}
