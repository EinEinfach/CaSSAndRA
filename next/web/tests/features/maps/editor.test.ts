import { describe, expect, it } from 'vitest';
import {
	History,
	addExclusion,
	addPoint,
	allLayers,
	clearLayer,
	distanceToSegment,
	emptyShape,
	hitPoint,
	isClosed,
	layerName,
	movePoint,
	perimeterLayer,
	pointsOf,
	problems,
	removePoint,
	roundPoint,
	sameLayer,
	type Layer
} from '#features/maps/editor.ts';
import { garden, pts } from './fixtures.ts';

const ex0: Layer = { kind: 'exclusion', index: 0 };
const dock: Layer = { kind: 'dock' };
const wire: Layer = { kind: 'searchWire' };

describe('layers', () => {
	it('names and kinds', () => {
		expect([perimeterLayer, ex0, dock, wire].map(layerName)).toEqual([
			'Perimeter',
			'Exclusion 1',
			'Dock path',
			'Search wire'
		]);
		expect([perimeterLayer, ex0, dock, wire].map(isClosed)).toEqual([true, true, false, false]);
		expect(sameLayer(ex0, { kind: 'exclusion', index: 0 })).toBe(true);
		expect(sameLayer(ex0, { kind: 'exclusion', index: 1 })).toBe(false);
		expect(sameLayer(dock, wire)).toBe(false);
		expect(allLayers(garden()).map(layerName)).toEqual([
			'Perimeter',
			'Exclusion 1',
			'Dock path',
			'Search wire'
		]);
	});

	it('reads points of every layer, empty for a missing exclusion', () => {
		const m = garden();
		expect(pointsOf(m, ex0)).toBe(m.exclusions[0]);
		expect(pointsOf(m, wire)).toBe(m.searchWire);
		expect(pointsOf(m, { kind: 'exclusion', index: 5 })).toEqual([]);
	});
});

describe('addPoint', () => {
	it('appends to lines and to polygons with fewer than 3 points', () => {
		let m = emptyShape('x');
		m = addPoint(m, perimeterLayer, { x: 0, y: 0 }).map;
		m = addPoint(m, perimeterLayer, { x: 5, y: 0 }).map;
		const r = addPoint(m, perimeterLayer, { x: 5, y: 5 });
		expect(r.index).toBe(2);
		expect(r.map.perimeter).toEqual(pts(0, 0, 5, 0, 5, 5));

		const d = addPoint(garden(), dock, { x: 9, y: 9 });
		expect(d.index).toBe(2);
		expect(d.map.dock.at(-1)).toEqual({ x: 9, y: 9 });
	});

	it('puts a polygon point on the nearest edge', () => {
		// near the bottom edge (0,0)-(10,0) -> between index 0 and 1
		const r = addPoint(garden(), perimeterLayer, { x: 5, y: -0.3 });
		expect(r.index).toBe(1);
		expect(r.map.perimeter.slice(0, 3)).toEqual(pts(0, 0, 5, -0.3, 10, 0));
		// near the closing edge (0,10)-(0,0) -> appended at the end
		expect(addPoint(garden(), perimeterLayer, { x: -0.2, y: 5 }).index).toBe(4);
	});

	it('rounds to centimeters and leaves the input untouched', () => {
		const m = garden();
		const r = addPoint(m, wire, { x: 1.23456, y: -0.005 });
		expect(r.map.searchWire).toEqual([{ x: 1.23, y: -0 }]);
		expect(m.searchWire).toEqual([]);
		expect(roundPoint({ x: 0.125, y: 2 })).toEqual({ x: 0.13, y: 2 });
	});
});

describe('editing', () => {
	it('moves and removes points', () => {
		const moved = movePoint(garden(), ex0, 1, { x: 4.444, y: 2 });
		expect(moved.exclusions[0][1]).toEqual({ x: 4.44, y: 2 });
		expect(removePoint(garden(), perimeterLayer, 0).perimeter).toEqual(pts(10, 0, 10, 10, 0, 10));
	});

	it('adds, removes and clears layers', () => {
		const { map, layer } = addExclusion(garden());
		expect(layer).toEqual({ kind: 'exclusion', index: 1 });
		expect(map.exclusions).toHaveLength(2);
		expect(clearLayer(map, ex0).exclusions).toEqual([[]]);
		expect(clearLayer(garden(), dock).dock).toEqual([]);
		expect(clearLayer(garden(), perimeterLayer).perimeter).toEqual([]);
	});
});

describe('hitPoint', () => {
	it('finds the nearest point within the radius', () => {
		expect(hitPoint(garden(), { x: 9.8, y: 0.1 }, 0.5)).toEqual({
			layer: perimeterLayer,
			index: 1
		});
		expect(hitPoint(garden(), { x: 5, y: 5 }, 0.5)).toBeNull();
	});

	it('prefers the edited layer where points overlap', () => {
		const m = { ...garden(), searchWire: pts(0, 0, 5, 5) };
		expect(hitPoint(m, { x: 0, y: 0 }, 0.5)?.layer).toEqual(perimeterLayer);
		expect(hitPoint(m, { x: 0, y: 0 }, 0.5, wire)).toEqual({ layer: wire, index: 0 });
	});
});

describe('distanceToSegment', () => {
	it('measures to the segment, not the line', () => {
		expect(distanceToSegment({ x: 5, y: 3 }, { x: 0, y: 0 }, { x: 10, y: 0 })).toBe(3);
		expect(distanceToSegment({ x: 13, y: 4 }, { x: 0, y: 0 }, { x: 10, y: 0 })).toBe(5);
		expect(distanceToSegment({ x: 3, y: 4 }, { x: 0, y: 0 }, { x: 0, y: 0 })).toBe(5);
	});
});

describe('problems', () => {
	it('is empty for a valid map', () => {
		expect(problems(garden())).toEqual([]);
	});

	it('lists what blocks saving, like the backend', () => {
		const m = {
			name: ' ',
			perimeter: pts(0, 0),
			exclusions: [pts(1, 1)],
			dock: pts(1, 1),
			searchWire: pts(2, 2)
		};
		expect(problems(m)).toEqual([
			'Give the map a name.',
			'The perimeter needs at least 3 points.',
			'Exclusion 1 needs at least 3 points.',
			'The dock path needs at least 2 points.',
			'The search wire needs at least 2 points.'
		]);
	});
});

describe('History', () => {
	it('undoes and redoes', () => {
		const h = new History(1);
		h.push(2);
		h.push(3);
		expect([h.undo(), h.undo(), h.undo()]).toEqual([2, 1, 1]);
		expect(h.canUndo).toBe(false);
		expect([h.redo(), h.redo(), h.redo()]).toEqual([2, 3, 3]);
		expect(h.canRedo).toBe(false);
	});

	it('drops the redo branch on a new change and keeps a limit', () => {
		const h = new History(0, 2);
		h.push(1);
		h.undo();
		h.push(5);
		expect(h.canRedo).toBe(false);
		h.push(6);
		h.push(7);
		expect([h.undo(), h.undo(), h.undo()]).toEqual([6, 5, 5]);
	});
});
