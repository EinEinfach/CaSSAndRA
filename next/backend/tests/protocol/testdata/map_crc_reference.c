// Reference for the Sunray map CRC (map.cpp: Point::setXY, Point::crc).
// Used to compute the expected values in mapcrc_test.go.
// Reads "x y" lines (as sent in AT+W) from stdin, prints the CRC for
// Arduino (short px/py) and Linux (float px/py).
#include <stdio.h>
#include <stdlib.h>
int main(void) {
  char xs[64], ys[64];
  long arduino = 0, linux_ = 0;
  while (scanf("%63s %63s", xs, ys) == 2) {
    float ax = (float)atof(xs), ay = (float)atof(ys); // String::toFloat
    short spx = ax * 100; short spy = ay * 100;       // Arduino
    float fpx = ax * 100; float fpy = ay * 100;       // Linux
    arduino += (spx + spy);
    linux_ += (long)(fpx + fpy);
  }
  printf("arduino=%ld linux=%ld\n", arduino, linux_);
  return 0;
}
