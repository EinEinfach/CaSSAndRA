import { describe, expect, it } from 'vitest';
import {
	MAX_SCALE,
	MIN_SCALE,
	fit,
	pan,
	resize,
	toScreen,
	toWorld,
	zoomAt
} from '#shared/viewport.ts';

describe('fit', () => {
	it('centers and scales the points into the canvas', () => {
		const vp = fit(
			[
				{ x: 0, y: 0 },
				{ x: 20, y: 10 }
			],
			448,
			248,
			24
		);
		// usable 400 x 200 px for 20 x 10 m -> 20 px/m
		expect(vp).toEqual({ centerX: 10, centerY: 5, scale: 20, width: 448, height: 248 });
	});

	it('uses the tighter axis', () => {
		const vp = fit(
			[
				{ x: 0, y: 0 },
				{ x: 10, y: 10 }
			],
			1000,
			200,
			0
		);
		expect(vp.scale).toBe(20);
	});

	it('handles no points and single points', () => {
		expect(fit([], 100, 100)).toMatchObject({ centerX: 0, centerY: 0, scale: 20 });
		const single = fit([{ x: 3, y: 4 }], 100, 100, 0);
		expect(single).toMatchObject({ centerX: 3, centerY: 4, scale: 100 });
	});

	it('clamps the scale', () => {
		const huge = fit(
			[
				{ x: 0, y: 0 },
				{ x: 100000, y: 0 }
			],
			100,
			100
		);
		expect(huge.scale).toBe(MIN_SCALE);
		const tiny = fit([{ x: 0, y: 0 }], 100000, 100000, 0);
		expect(tiny.scale).toBe(MAX_SCALE);
	});
});

describe('toScreen / toWorld', () => {
	const vp = { centerX: 10, centerY: 5, scale: 20, width: 400, height: 200 };

	it('maps the center to the canvas middle and flips y', () => {
		expect(toScreen(vp, { x: 10, y: 5 })).toEqual({ x: 200, y: 100 });
		expect(toScreen(vp, { x: 11, y: 6 })).toEqual({ x: 220, y: 80 });
	});

	it('are inverse to each other', () => {
		const p = { x: -3.25, y: 12.5 };
		const back = toWorld(vp, toScreen(vp, p));
		expect(back.x).toBeCloseTo(p.x);
		expect(back.y).toBeCloseTo(p.y);
	});
});

describe('zoomAt', () => {
	const vp = { centerX: 0, centerY: 0, scale: 10, width: 200, height: 200 };

	it('keeps the world point under the cursor', () => {
		const cursor = { x: 150, y: 50 };
		const before = toWorld(vp, cursor);
		const zoomed = zoomAt(vp, 2, cursor);
		const after = toWorld(zoomed, cursor);
		expect(zoomed.scale).toBe(20);
		expect(after.x).toBeCloseTo(before.x);
		expect(after.y).toBeCloseTo(before.y);
	});

	it('respects the scale limits', () => {
		expect(zoomAt(vp, 1e9, { x: 0, y: 0 }).scale).toBe(MAX_SCALE);
		expect(zoomAt(vp, 1e-9, { x: 0, y: 0 }).scale).toBe(MIN_SCALE);
	});
});

describe('pan and resize', () => {
	const vp = { centerX: 0, centerY: 0, scale: 10, width: 200, height: 200 };

	it('moves the content with the drag', () => {
		const moved = pan(vp, 20, 10);
		// dragging right/down shows what was left/up
		expect(moved.centerX).toBeCloseTo(-2);
		expect(moved.centerY).toBeCloseTo(1);
	});

	it('keeps the center on resize', () => {
		expect(resize(vp, 300, 100)).toEqual({ ...vp, width: 300, height: 100 });
	});
});
