import { describe, expect, it } from 'vitest';
import {
	canStartRoute,
	formatDistance,
	formatDuration,
	planMatches
} from '#features/tasks/plan.ts';
import { pts } from '../maps/fixtures.ts';
import { parameters, plan } from './fixtures.ts';

describe('plan', () => {
	it('matches the request it was computed for', () => {
		const p = plan({ selection: pts(0, 0, 1, 0, 1, 1) });
		expect(planMatches(p, { selection: pts(0, 0, 1, 0, 1, 1), parameters: parameters() })).toBe(
			true
		);
		expect(planMatches(p, { selection: pts(0, 0, 1, 0, 1, 2), parameters: parameters() })).toBe(
			false
		);
		expect(planMatches(p, { selection: [], parameters: parameters() })).toBe(false);
		expect(
			planMatches(p, { selection: p.selection, parameters: parameters({ angleDeg: 45 }) })
		).toBe(false);
	});

	it('starts a route only while the robot stands still', () => {
		expect(canStartRoute('idle')).toBe(true);
		expect(canStartRoute('docked')).toBe(true);
		expect(canStartRoute('charging')).toBe(true);
		for (const s of [
			'mow',
			'transit',
			'move',
			'docking',
			'map upload',
			'offline',
			'error'
		] as const) {
			expect(canStartRoute(s)).toBe(false);
		}
	});

	it('formats distances', () => {
		expect(formatDistance(812.4)).toBe('812 m');
		expect(formatDistance(1350)).toBe('1.4 km');
	});

	it('estimates the time at the mow speed, in steps of 5 minutes', () => {
		expect(formatDuration(1350, 0.25)).toBe('1 h 30 min');
		expect(formatDuration(100, 0.25)).toBe('5 min');
		expect(formatDuration(30, 0.25)).toBe('5 min');
		expect(formatDuration(100, 0)).toBe('');
	});
});
