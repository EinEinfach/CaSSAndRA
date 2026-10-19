import { describe, expect, it } from 'vitest';
import { PlanSession } from '#features/tasks/session.svelte.ts';
import { pts } from '../maps/fixtures.ts';
import { parameters, plan, task } from './fixtures.ts';

const mpp = 0.01; // 1 cm per pixel: grab radius 14 cm

function session() {
	const s = new PlanSession();
	s.useDefaults(parameters());
	return s;
}

describe('PlanSession', () => {
	it('has nothing to send until the defaults are known', () => {
		const s = new PlanSession();
		expect(s.part).toBeNull();
		expect(s.drafted).toBeNull();
		s.useDefaults(parameters());
		expect(s.drafted).toEqual([{ selection: [], parameters: parameters() }]);
	});

	it('keeps parameters once set; later defaults only affect new parts', () => {
		const s = session();
		s.part!.parameters.angleDeg = 30;
		s.useDefaults(parameters({ angleDeg: 90 }));
		expect(s.drafted![0].parameters.angleDeg).toBe(30);
		s.reset();
		expect(s.drafted![0].parameters.angleDeg).toBe(90);
	});

	it('draws a rectangle by dragging and drops a slip', () => {
		const s = session();
		s.setTool('rectangle');
		expect(s.drafted).toBeNull();

		expect(s.press({ x: 1, y: 1 }, mpp)).toBe(true);
		s.move({ x: 2, y: 4 });
		s.move({ x: 4, y: 3 });
		s.release();
		expect(s.selection).toEqual(pts(1, 1, 4, 1, 4, 3, 1, 3));
		expect(s.drafted![0].selection).toEqual(s.selection);

		s.press({ x: 5, y: 5 }, mpp);
		s.move({ x: 5.2, y: 5.1 });
		s.release();
		expect(s.selection).toEqual([]);
	});

	it('adds polygon corners by tapping and moves them by dragging', () => {
		const s = session();
		s.setTool('polygon');
		s.tap({ x: 0, y: 0 });
		s.tap({ x: 3.333, y: 0 });
		expect(s.drafted).toBeNull(); // two corners are no area
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
		const s = session();
		expect(s.press({ x: 1, y: 1 }, mpp)).toBe(false);
		s.tap({ x: 1, y: 1 });
		expect(s.selection).toEqual([]);
	});

	it('keeps a rectangle as polygon to adjust it, and drops it for the whole garden', () => {
		const s = session();
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

	it('has several parts, each with its own area and parameters', () => {
		const s = session();
		s.part!.parameters.pattern = 'rings';
		s.addPart();
		expect(s.current).toBe(1);
		expect(s.part!.parameters.pattern).toBe('rings'); // taken from the current part
		s.part!.parameters.pattern = 'squares';
		s.setTool('rectangle');
		s.press({ x: 0, y: 0 }, mpp);
		s.move({ x: 2, y: 2 });
		s.release();

		expect(s.drafted!.map((p) => [p.parameters.pattern, p.selection.length])).toEqual([
			['rings', 0],
			['squares', 4]
		]);
		s.selectPart(0);
		expect(s.tool).toBe('all');
		s.removePart();
		expect(s.parts).toHaveLength(1);
		expect(s.part!.parameters.pattern).toBe('squares');
		s.removePart(); // the last part stays
		expect(s.parts).toHaveLength(1);
	});

	it('needs an area in every part', () => {
		const s = session();
		s.addPart();
		s.setTool('polygon');
		expect(s.drafted).toBeNull();
	});

	it('edits a saved task and saves it with a name', () => {
		const s = session();
		expect(s.toTask('m1')).toBeNull(); // no name
		s.name = '  Front ';
		expect(s.toTask('m1')).toEqual({ name: 'Front', mapId: 'm1', parts: s.drafted });

		const sel = pts(1, 1, 4, 1, 4, 4);
		s.edit(
			task('t1', 'Back', {
				parts: [
					{ selection: [], parameters: parameters() },
					{ selection: sel, parameters: parameters({ widthM: 0.3 }) }
				]
			})
		);
		expect(s.editing).toBe('t1');
		expect(s.name).toBe('Back');
		expect(s.parts.map((p) => p.tool)).toEqual(['all', 'polygon']);
		expect(s.drafted![1]).toEqual({ selection: sel, parameters: parameters({ widthM: 0.3 }) });

		s.reset();
		expect(s.editing).toBeNull();
		expect(s.name).toBe('');
		expect(s.parts).toHaveLength(1);
	});

	it('chooses saved tasks in the order they are tapped', () => {
		const s = session();
		s.toggle('b');
		s.toggle('a');
		s.toggle('c');
		s.toggle('a');
		expect(s.chosen).toEqual(['b', 'c']);
		s.keepChosen(['c']);
		expect(s.chosen).toEqual(['c']);
	});

	it('shows the plan it finds when the page opens, but only the first one', () => {
		const s = session();
		const sel = pts(0, 0, 2, 0, 2, 2);
		s.adopt(plan({ parts: [{ selection: sel, parameters: parameters({ pattern: 'rings' }) }] }));
		expect(s.tool).toBe('polygon');
		expect(s.drafted).toEqual([{ selection: sel, parameters: parameters({ pattern: 'rings' }) }]);

		s.adopt(plan({ parts: [{ selection: [], parameters: parameters({ pattern: 'squares' }) }] }));
		expect(s.drafted![0].parameters.pattern).toBe('rings');
	});

	it('chooses the tasks of a plan made from saved tasks', () => {
		const s = session();
		s.adopt(plan({ taskIds: ['b', 'a'] }));
		expect(s.chosen).toEqual(['b', 'a']);
		expect(s.drafted![0].selection).toEqual([]); // the editor stays fresh
	});

	it('starts fresh when there was no plan', () => {
		const s = new PlanSession();
		s.adopt(null);
		s.adopt(plan());
		expect(s.parts).toEqual([]);
	});
});
