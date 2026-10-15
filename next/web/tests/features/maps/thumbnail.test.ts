import { describe, expect, it } from 'vitest';
import { emptyShape } from '#features/maps/editor.ts';
import { thumbnail } from '#features/maps/thumbnail.ts';
import { garden, pts } from './fixtures.ts';

describe('thumbnail', () => {
	it('fits the map into the square with y up', () => {
		const t = thumbnail({ ...garden(), exclusions: [], dock: [] }, 24, 2);
		// 10 m -> 20 px, bottom-left (0,0) at (2,22)
		expect(t.perimeter).toBe('M2 22 L22 22 L22 2 L2 2 Z');
	});

	it('centers the short side and draws exclusions and dock', () => {
		const m = {
			...emptyShape(),
			perimeter: pts(0, 0, 10, 0, 10, 5),
			exclusions: [pts(1, 1, 2, 1, 2, 2)],
			dock: pts(0, 0, 0, 1)
		};
		const t = thumbnail(m, 24, 2);
		expect(t.perimeter).toBe('M2 17 L22 17 L22 7 Z');
		expect(t.exclusions).toEqual(['M4 15 L6 15 L6 13 Z']);
		expect(t.dock).toBe('M2 17 L2 15');
	});

	it('is empty for an empty map', () => {
		expect(thumbnail(emptyShape(), 24)).toEqual({ perimeter: '', exclusions: [], dock: '' });
	});
});
