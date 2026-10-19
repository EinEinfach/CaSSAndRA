import { describe, expect, it } from 'vitest';
import { area, hit, isUsable, rectangle, roundPoint } from '#features/tasks/selection.ts';
import { pts } from '../maps/fixtures.ts';

describe('selection', () => {
	it('builds a counter-clockwise rectangle from any two corners, in centimeters', () => {
		expect(rectangle({ x: 4.123, y: 1 }, { x: 1, y: 3.456 })).toEqual(
			pts(1, 1, 4.12, 1, 4.12, 3.46, 1, 3.46)
		);
	});

	it('computes the area in any orientation', () => {
		expect(area(pts(0, 0, 4, 0, 4, 3))).toBe(6);
		expect(area(pts(0, 0, 4, 3, 4, 0))).toBe(6);
	});

	it('accepts only selections with an area', () => {
		expect(isUsable(pts(0, 0, 1, 0, 1, 1))).toBe(true);
		expect(isUsable(pts(0, 0, 1, 0))).toBe(false);
		expect(isUsable(pts(0, 0, 0.3, 0, 0.3, 0.3, 0, 0.3))).toBe(false); // a slip of the finger
		expect(isUsable(pts(0, 0, 1, 1, 2, 2))).toBe(false); // on a line
	});

	it('finds the nearest point within the radius', () => {
		const corners = pts(0, 0, 1, 0, 1.2, 0);
		expect(hit(corners, { x: 1.15, y: 0 }, 0.5)).toBe(2);
		expect(hit(corners, { x: 5, y: 5 }, 0.5)).toBe(-1);
	});

	it('rounds to centimeters', () => {
		expect(roundPoint({ x: 1.005, y: -2.3449 })).toEqual({ x: 1, y: -2.34 });
	});
});
