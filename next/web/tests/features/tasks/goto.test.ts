import { describe, expect, it } from 'vitest';
import { GotoPicker } from '#features/tasks/goto.svelte.ts';

describe('GotoPicker', () => {
	it('places the goal only while picking, in centimeters', () => {
		const p = new GotoPicker();
		p.interact.tap!({ x: 1, y: 1 }, 0.01);
		expect(p.goal).toBeNull();

		p.start();
		p.interact.tap!({ x: 2.345, y: 1.004 }, 0.01);
		expect(p.goal).toEqual({ x: 2.35, y: 1 });
		p.interact.tap!({ x: 3, y: 3 }, 0.01);
		expect(p.goal).toEqual({ x: 3, y: 3 });

		p.cancel();
		expect(p.picking).toBe(false);
		expect(p.goal).toBeNull();
	});

	it('starts each pick without a goal', () => {
		const p = new GotoPicker();
		p.start();
		p.interact.tap!({ x: 1, y: 1 }, 0.01);
		p.start();
		expect(p.goal).toBeNull();
	});
});
