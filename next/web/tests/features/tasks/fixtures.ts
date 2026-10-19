// Shared test data for the tasks feature.
import type { Parameters, Plan } from '#features/tasks/types.ts';
import { pts } from '../maps/fixtures.ts';

export function parameters(overrides: Partial<Parameters> = {}): Parameters {
	return {
		pattern: 'lines',
		widthM: 0.18,
		angleDeg: 0,
		distanceToBorder: 1,
		mowArea: true,
		borderLaps: 1,
		mowExclusions: true,
		borderCcw: false,
		...overrides
	};
}

export function plan(overrides: Partial<Plan> = {}): Plan {
	return {
		mapId: 'm1',
		mapUpdatedAt: '2026-06-01T12:00:00Z',
		selection: [],
		parameters: parameters(),
		start: { x: 1, y: 2 },
		route: pts(1, 2, 0, 0, 10, 0, 10, 10),
		distanceM: 1350,
		createdAt: '2026-06-01T12:05:00Z',
		...overrides
	};
}
