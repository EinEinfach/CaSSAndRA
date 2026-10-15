package protocol

import (
	"strconv"

	"github.com/EinEinfach/CaSSAndRA/next/backend/geo"
)

// MapCRC is the map checksum the robot reports in AT+S (map_crc) once it
// has stored a map. The firmware sums all points in centimeters
// (map.cpp: Point::setXY, Point::crc), but the result depends on its
// platform and version: on Arduino each coordinate is truncated to a short,
// current Linux firmware keeps them float and truncates only each point's
// sum (Sunray 1.0.324 on Linux still computes like Arduino). Both use single
// precision, so e.g. 40.94 becomes 4093 cm on Arduino.
type MapCRC struct {
	Arduino int64
	Linux   int64
}

// Matches reports whether the robot's map_crc fits either platform.
func (c MapCRC) Matches(reported int64) bool {
	return reported == c.Arduino || reported == c.Linux
}

// MapChecksum returns the map_crc the robot will report after storing m
// with MapUpload. It uses the coordinates exactly as MapUpload sends them.
func MapChecksum(m Map) MapCRC {
	var crc MapCRC
	add := func(pts []geo.Point) {
		for _, p := range pts {
			// String::toFloat parses as double and converts to float.
			x, y := sentCoord(p.X), sentCoord(p.Y)
			// Explicit conversions keep Go from fusing the float32 operations.
			px, py := float32(x*100), float32(y*100)
			crc.Arduino += int64(int16(px)) + int64(int16(py))
			crc.Linux += int64(float32(px + py))
		}
	}
	add(m.Perimeter)
	for _, ex := range m.Exclusions {
		add(ex)
	}
	add(m.Dock)
	add(m.Way)
	return crc
}

func sentCoord(v float64) float32 {
	f, _ := strconv.ParseFloat(formatCoord(v), 64) // formatCoord always yields a number
	return float32(f)
}
