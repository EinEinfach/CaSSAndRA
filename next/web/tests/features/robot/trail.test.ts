import { describe, expect, it } from 'vitest';
import { extendTrail } from '#features/robot/trail.ts';

const opts = { maxPoints: 3, minDistanceM: 0.1, maxJumpM: 5 };

describe('extendTrail', () => {
	it('appends points without changing the input', () => {
		const trail = [{ x: 0, y: 0 }];
		const next = extendTrail(trail, { x: 1, y: 0 }, opts);
		expect(next).toEqual([
			{ x: 0, y: 0 },
			{ x: 1, y: 0 }
		]);
		expect(trail).toHaveLength(1);
	});

	it('ignores tiny movements', () => {
		const trail = [{ x: 0, y: 0 }];
		expect(extendTrail(trail, { x: 0.05, y: 0 }, opts)).toBe(trail);
	});

	it('starts over after a jump', () => {
		expect(extendTrail([{ x: 0, y: 0 }], { x: 10, y: 0 }, opts)).toEqual([{ x: 10, y: 0 }]);
	});

	it('drops the oldest points beyond the limit', () => {
		let trail: { x: number; y: number }[] = [];
		for (let i = 0; i < 5; i++) trail = extendTrail(trail, { x: i, y: 0 }, opts);
		expect(trail.map((p) => p.x)).toEqual([2, 3, 4]);
	});

	it('starts with the first point', () => {
		expect(extendTrail([], { x: 1, y: 1 })).toEqual([{ x: 1, y: 1 }]);
	});
});
