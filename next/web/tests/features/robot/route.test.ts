import { describe, expect, it } from 'vitest';
import { followsRoute, routeProgress } from '#features/robot/route.ts';

describe('route', () => {
	it('progress is the share of route points behind the robot', () => {
		expect(routeProgress(25, 100)).toBe(0.25);
		expect(routeProgress(0, 100)).toBe(0);
		expect(routeProgress(150, 100)).toBe(1);
		expect(routeProgress(-1, 100)).toBe(0);
		expect(routeProgress(3, 0)).toBe(0);
	});

	it('applies while the robot follows the route', () => {
		expect(followsRoute('mow')).toBe(true);
		expect(followsRoute('transit')).toBe(true);
		expect(followsRoute('idle')).toBe(false);
		expect(followsRoute('docking')).toBe(false);
	});
});
