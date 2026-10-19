import { describe, expect, it } from 'vitest';
import { PlanSession } from '#features/tasks/session.svelte.ts';
import { pts } from '../maps/fixtures.ts';
import { parameters, plan } from './fixtures.ts';

const mpp = 0.01; // 1 cm per pixel: grab radius 14 cm

describe('PlanSession', () => {
	it('has no request until parameters are known', () => {
		const s = new PlanSession();
		expect(s.request).toBeNull();
		s.useDefaults(parameters());
		expect(s.request).toEqual({ selection: [], parameters: parameters() });
	});

	it('keeps parameters once set; later defaults do not overwrite them', () => {
		const s = new PlanSession();
		s.useDefaults(parameters());
		s.parameters!.angleDeg = 30;
		s.useDefaults(parameters({ angleDeg: 90 }));
		expect(s.request?.parameters.angleDeg).toBe(30);
	});

	it('draws a rectangle by dragging and drops a slip', () => {
		const s = new PlanSession();
		s.useDefaults(parameters());
		s.setTool('rectangle');
		expect(s.request).toBeNull();

		expect(s.press({ x: 1, y: 1 }, mpp)).toBe(true);
		s.move({ x: 2, y: 4 });
		s.move({ x: 4, y: 3 });
		s.release();
		expect(s.selection).toEqual(pts(1, 1, 4, 1, 4, 3, 1, 3));
		expect(s.request?.selection).toEqual(s.selection);

		s.press({ x: 5, y: 5 }, mpp);
		s.move({ x: 5.2, y: 5.1 });
		s.release();
		expect(s.selection).toEqual([]);
	});

	it('adds polygon corners by tapping and moves them by dragging', () => {
		const s = new PlanSession();
		s.useDefaults(parameters());
		s.setTool('polygon');
		s.tap({ x: 0, y: 0 });
		s.tap({ x: 3.333, y: 0 });
		expect(s.request).toBeNull(); // two corners are no area
		s.tap({ x: 3, y: 3 });
		expect(s.selection).toEqual(pts(0, 0, 3.33, 0, 3, 3));

		expect(s.press({ x: 3.4, y: 0.05 }, mpp)).toBe(true);
		s.move({ x: 4, y: 0 });
		s.release();
		expect(s.selection).toEqual(pts(0, 0, 4, 0, 3, 3));

		expect(s.press({ x: 8, y: 8 }, mpp)).toBe(false); // not on a corner: the map pans
		s.removeLastCorner();
		expect(s.selection).toEqual(pts(0, 0, 4, 0));
	});

	it('pans the map in "whole garden" and ignores taps there', () => {
		const s = new PlanSession();
		expect(s.press({ x: 1, y: 1 }, mpp)).toBe(false);
		s.tap({ x: 1, y: 1 });
		expect(s.selection).toEqual([]);
	});

	it('keeps a rectangle as polygon to adjust it, and drops it for the whole garden', () => {
		const s = new PlanSession();
		s.setTool('rectangle');
		s.press({ x: 0, y: 0 }, mpp);
		s.move({ x: 2, y: 2 });
		s.release();
		s.setTool('polygon');
		expect(s.selection).toHaveLength(4);
		expect(s.canvasLayers.edit?.points).toHaveLength(4);
		s.setTool('rectangle');
		expect(s.selection).toEqual([]);
		s.setTool('polygon');
		s.tap({ x: 1, y: 1 });
		s.setTool('all');
		expect(s.selection).toEqual([]);
		expect(s.canvasLayers).toEqual({ selection: [], edit: null });
	});

	it('shows the plan it finds when the page opens, but only the first one', () => {
		const s = new PlanSession();
		s.useDefaults(parameters());
		const sel = pts(0, 0, 2, 0, 2, 2);
		s.adopt(plan({ selection: sel, parameters: parameters({ pattern: 'rings' }) }));
		expect(s.tool).toBe('polygon');
		expect(s.request).toEqual({ selection: sel, parameters: parameters({ pattern: 'rings' }) });

		s.adopt(plan({ selection: [], parameters: parameters({ pattern: 'squares' }) }));
		expect(s.request?.parameters.pattern).toBe('rings');
	});

	it('starts fresh when there was no plan', () => {
		const s = new PlanSession();
		s.adopt(null);
		s.adopt(plan());
		expect(s.parameters).toBeNull();
	});
});
