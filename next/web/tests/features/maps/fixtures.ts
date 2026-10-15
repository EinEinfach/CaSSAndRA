import type { GardenMap } from '#features/maps/types.ts';
import type { Point } from '#shared/viewport.ts';

export const pts = (...c: number[]): Point[] =>
	Array.from({ length: c.length / 2 }, (_, i) => ({ x: c[2 * i], y: c[2 * i + 1] }));

export function garden(id = 'm1', name = 'Garden'): GardenMap {
	return {
		id,
		name,
		perimeter: pts(0, 0, 10, 0, 10, 10, 0, 10),
		exclusions: [pts(2, 2, 3, 2, 3, 3)],
		dock: pts(1, 1, 1, 2),
		searchWire: [],
		updatedAt: '2026-06-01T12:00:00Z'
	};
}
