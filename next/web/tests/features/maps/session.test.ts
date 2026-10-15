import { describe, expect, it } from 'vitest';
import { emptyShape } from '#features/maps/editor.ts';
import { EditorSession, GRAB_PX } from '#features/maps/session.svelte.ts';
import { garden, pts } from './fixtures.ts';

const mpp = 0.05; // 20 px per meter -> grab radius 0.7 m

describe('EditorSession', () => {
	it('starts on the perimeter without selection and nothing to undo', () => {
		const s = new EditorSession(garden());
		expect(s.layer).toEqual({ kind: 'perimeter' });
		expect(s.selected).toBeNull();
		expect([s.canUndo, s.canRedo]).toEqual([false, false]);
		expect(s.problems).toEqual([]);
		expect(GRAB_PX * mpp).toBeCloseTo(0.7);
	});

	it('draws a new perimeter by tapping', () => {
		const s = new EditorSession(emptyShape('New'));
		expect(s.problems).toContain('The perimeter needs at least 3 points.');
		s.tap({ x: 0, y: 0 }, mpp);
		s.tap({ x: 10, y: 0 }, mpp);
		s.tap({ x: 10, y: 10 }, mpp);
		expect(s.draft.perimeter).toEqual(pts(0, 0, 10, 0, 10, 10));
		expect(s.selected).toBe(2);
		expect(s.problems).toEqual([]);
		expect(s.canvasLayers.edit).toEqual({ points: s.draft.perimeter, closed: true, selected: 2 });
	});

	it('selects a point by tapping it, even on another layer', () => {
		const s = new EditorSession(garden());
		s.tap({ x: 1.1, y: 2.1 }, mpp);
		expect(s.layer).toEqual({ kind: 'dock' });
		expect(s.selected).toBe(1);
		expect(s.canUndo).toBe(false);
	});

	it('drags a point as one undo step', () => {
		const s = new EditorSession(garden());
		expect(s.press({ x: 5, y: 5 }, mpp)).toBe(false); // nothing there
		expect(s.press({ x: 10, y: 10 }, mpp)).toBe(true);
		s.move({ x: 11, y: 10 });
		s.move({ x: 12, y: 11 });
		s.release();
		expect(s.draft.perimeter[2]).toEqual({ x: 12, y: 11 });
		s.undo();
		expect(s.draft.perimeter[2]).toEqual({ x: 10, y: 10 });
		expect(s.canUndo).toBe(false);
		s.redo();
		expect(s.draft.perimeter[2]).toEqual({ x: 12, y: 11 });
	});

	it('ignores moves without a drag and a drag without movement', () => {
		const s = new EditorSession(garden());
		s.move({ x: 50, y: 50 });
		s.release();
		s.press({ x: 0, y: 0 }, mpp);
		s.release();
		expect(s.draft).toEqual(garden());
		expect(s.canUndo).toBe(false);
	});

	it('deletes the selected point and keeps a neighbour selected', () => {
		const s = new EditorSession(garden());
		s.deleteSelected(); // nothing selected
		expect(s.canUndo).toBe(false);
		s.tap({ x: 0, y: 10 }, mpp); // last perimeter point
		s.deleteSelected();
		expect(s.draft.perimeter).toHaveLength(3);
		expect(s.selected).toBe(2);
		s.tap({ x: 1, y: 2 }, mpp);
		s.deleteSelected();
		s.deleteSelected();
		expect(s.draft.dock).toEqual([]);
		expect(s.selected).toBeNull();
	});

	it('adds and removes exclusions', () => {
		const s = new EditorSession(garden());
		s.newExclusion();
		expect(s.layer).toEqual({ kind: 'exclusion', index: 1 });
		expect(s.problems).toContain('Exclusion 2 needs at least 3 points.');
		s.clear();
		expect(s.draft.exclusions).toHaveLength(1);
		expect(s.layer).toEqual({ kind: 'perimeter' });
	});

	it('clears lines and polygons', () => {
		const s = new EditorSession(garden());
		s.selectLayer({ kind: 'dock' });
		expect(s.isLayer({ kind: 'dock' })).toBe(true);
		s.clear();
		expect(s.draft.dock).toEqual([]);
	});

	it('leaves an exclusion that undo removed', () => {
		const s = new EditorSession(garden());
		s.newExclusion();
		s.undo();
		expect(s.layer).toEqual({ kind: 'perimeter' });
	});

	it('keeps the name out of the undo history', () => {
		const s = new EditorSession(garden());
		s.name = 'Front lawn';
		expect(s.canUndo).toBe(false);
		expect(s.result.name).toBe('Front lawn');
		s.name = '';
		expect(s.problems).toEqual(['Give the map a name.']);
	});
});
