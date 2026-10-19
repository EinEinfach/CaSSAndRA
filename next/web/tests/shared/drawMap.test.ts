import { describe, expect, it } from 'vitest';
import { drawMap, mapPoints, type MapColors } from '#shared/drawMap.ts';
import { recordingContext } from './recordingContext.ts';

const colors: MapColors = {
	background: 'bg',
	lawn: 'lawn',
	border: 'border',
	exclusion: 'exclusion',
	dock: 'dock',
	way: 'way',
	wayDone: 'done',
	trail: 'trail',
	target: 'target',
	robot: 'robot',
	robotOutline: 'outline',
	wire: 'wire',
	selection: 'selection',
	selectionFill: 'selectionFill',
	handle: 'handle',
	handleFill: 'handleFill'
};

// 10 px per meter, world (0,0) at screen (100,100), y up.
const vp = { centerX: 0, centerY: 0, scale: 10, width: 200, height: 200 };

describe('drawMap', () => {
	it('clears the canvas with the background', () => {
		const ctx = recordingContext();
		drawMap(ctx, vp, {}, colors);
		expect(ctx.rects).toEqual(['bg']);
		expect(ctx.shapes).toEqual([]);
	});

	it('draws the lawn as a closed, filled and outlined polygon in screen coordinates', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				perimeter: [
					{ x: 0, y: 0 },
					{ x: 5, y: 0 },
					{ x: 5, y: 2 }
				]
			},
			colors
		);
		const [fill, stroke] = ctx.shapes;
		expect(fill).toMatchObject({ op: 'fill', color: 'lawn', closed: true });
		expect(fill.points).toEqual([
			[100, 100],
			[150, 100],
			[150, 80]
		]);
		expect(stroke).toMatchObject({ op: 'stroke', color: 'border' });
	});

	it('fills exclusions and skips empty ones', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				exclusions: [
					[],
					[
						{ x: 1, y: 1 },
						{ x: 2, y: 1 },
						{ x: 2, y: 2 }
					]
				]
			},
			colors
		);
		expect(ctx.shapes).toHaveLength(1);
		expect(ctx.shapes[0]).toMatchObject({ op: 'fill', color: 'exclusion', closed: true });
	});

	it('draws the selection filled with a dashed outline below the route', () => {
		const ctx = recordingContext();
		const selection = [
			{ x: 0, y: 0 },
			{ x: 2, y: 0 },
			{ x: 2, y: 2 }
		];
		drawMap(
			ctx,
			vp,
			{
				selection,
				way: [
					{ x: 0, y: 0 },
					{ x: 1, y: 1 }
				]
			},
			colors
		);
		const [fill, outline, way] = ctx.shapes;
		expect(fill).toMatchObject({ op: 'fill', color: 'selectionFill', closed: true, dashed: false });
		expect(outline).toMatchObject({ op: 'stroke', color: 'selection', closed: true, dashed: true });
		expect(way).toMatchObject({ op: 'stroke', color: 'way', dashed: false });
	});

	it('skips a selection of less than three points and keeps it out of the fit', () => {
		const ctx = recordingContext();
		const selection = [
			{ x: 0, y: 0 },
			{ x: 2, y: 0 }
		];
		drawMap(ctx, vp, { selection }, colors);
		expect(ctx.shapes).toEqual([]);
		expect(mapPoints({ selection: [...selection, { x: 9, y: 9 }] })).toEqual([]);
	});

	it('splits the route into done and open parts that meet at the current point', () => {
		const ctx = recordingContext();
		const way = [0, 1, 2, 3].map((i) => ({ x: i, y: 0 }));
		drawMap(ctx, vp, { way, wayDoneIndex: 2 }, colors);
		const done = ctx.shapes.find((s) => s.color === 'done')!;
		const open = ctx.shapes.find((s) => s.color === 'way')!;
		expect(done.points.map(([x]) => x)).toEqual([100, 110, 120]);
		expect(open.points.map(([x]) => x)).toEqual([110, 120, 130]);
	});

	it('draws the whole route as open without progress', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				way: [
					{ x: 0, y: 0 },
					{ x: 1, y: 0 }
				]
			},
			colors
		);
		expect(ctx.shapes.map((s) => s.color)).toEqual(['way']);
	});

	it('draws the dock path dashed with the station as a dot', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				dock: [
					{ x: 0, y: 1 },
					{ x: 0, y: -2 }
				]
			},
			colors
		);
		expect(ctx.shapes[0]).toMatchObject({ op: 'stroke', color: 'dock', dashed: true });
		expect(ctx.shapes[1]).toMatchObject({ op: 'fill', color: 'dock', dashed: false });
		expect(ctx.shapes[1].arcs).toEqual([[100, 120, 5]]);
	});

	it('draws trail, target and robot on top', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				perimeter: [
					{ x: 0, y: 0 },
					{ x: 1, y: 0 },
					{ x: 1, y: 1 }
				],
				trail: [
					{ x: 0, y: 0 },
					{ x: 1, y: 1 }
				],
				target: { x: 2, y: 2 },
				robot: { position: { x: 1, y: 1 }, headingRad: 0 }
			},
			colors
		);
		expect(ctx.shapes.map((s) => s.color)).toEqual([
			'lawn',
			'border',
			'trail',
			'target',
			'robot',
			'outline'
		]);
		expect(ctx.shapes[3].arcs).toEqual([[120, 80, 4]]);
	});

	it('draws the robot picture centered and turned to the heading instead of the arrow', () => {
		const ctx = recordingContext();
		const image = {} as CanvasImageSource;
		drawMap(
			ctx,
			vp,
			{
				robot: { position: { x: 1, y: 1 }, headingRad: Math.PI / 2 },
				robotPicture: { image, sizeM: 5 }
			},
			colors
		);
		expect(ctx.shapes).toEqual([]);
		expect(ctx.images).toEqual([
			{ image, at: [110, 90], rotation: -Math.PI / 2, box: [-25, -25, 50, 50] }
		]);
	});

	it('keeps a small robot picture visible when zoomed out', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				robot: { position: { x: 0, y: 0 }, headingRad: 0 },
				robotPicture: { image: {} as CanvasImageSource, sizeM: 0.5 }
			},
			colors
		);
		expect(ctx.images[0].box).toEqual([-14, -14, 28, 28]);
	});

	it('does not draw a trail of one point', () => {
		const ctx = recordingContext();
		drawMap(ctx, vp, { trail: [{ x: 0, y: 0 }] }, colors);
		expect(ctx.shapes).toEqual([]);
	});

	it('draws the search wire as a dotted line', () => {
		const ctx = recordingContext();
		drawMap(
			ctx,
			vp,
			{
				searchWire: [
					{ x: 0, y: 0 },
					{ x: 1, y: 0 }
				]
			},
			colors
		);
		expect(ctx.shapes).toEqual([
			expect.objectContaining({ op: 'stroke', color: 'wire', dashed: true, closed: false })
		]);
	});

	it('draws edit handles above everything, the selected one larger', () => {
		const ctx = recordingContext();
		const points = [
			{ x: 0, y: 0 },
			{ x: 1, y: 0 },
			{ x: 1, y: 1 }
		];
		drawMap(
			ctx,
			vp,
			{
				robot: { position: { x: 5, y: 5 }, headingRad: 0 },
				edit: { points, closed: true, selected: 1 }
			},
			colors
		);
		const handles = ctx.shapes.filter((s) => s.arcs.length > 0 && s.op === 'fill');
		expect(handles.map((h) => [h.color, h.arcs[0][2]])).toEqual([
			['handleFill', 6],
			['handle', 9],
			['handleFill', 6]
		]);
		const outline = ctx.shapes.find(
			(s) => s.op === 'stroke' && s.color === 'handle' && s.points.length === 3
		);
		expect(outline?.closed).toBe(true);
		// handles come after the robot
		expect(ctx.shapes.findIndex((s) => s.color === 'robot')).toBeLessThan(
			ctx.shapes.findIndex((s) => s.color === 'handleFill')
		);
	});

	it('draws an open polygon outline while it has only two points', () => {
		const ctx = recordingContext();
		const points = [
			{ x: 0, y: 0 },
			{ x: 1, y: 0 }
		];
		drawMap(ctx, vp, { edit: { points, closed: true, selected: null } }, colors);
		const outline = ctx.shapes.find((s) => s.op === 'stroke' && s.points.length === 2);
		expect(outline?.closed).toBe(false);
		expect(ctx.shapes.filter((s) => s.op === 'fill' && s.color === 'handle')).toEqual([]);
	});
});

describe('mapPoints', () => {
	it('collects everything the view should show', () => {
		expect(
			mapPoints({
				perimeter: [{ x: 0, y: 0 }],
				exclusions: [[{ x: 1, y: 1 }]],
				dock: [{ x: 2, y: 2 }],
				searchWire: [{ x: 2.5, y: 2.5 }],
				way: [{ x: 3, y: 3 }],
				trail: [{ x: 9, y: 9 }],
				robot: { position: { x: 4, y: 4 }, headingRad: 0 },
				edit: { points: [{ x: 8, y: 8 }], closed: false, selected: null }
			}).map((p) => p.x)
		).toEqual([0, 1, 2, 2.5, 3, 4]);
	});
});
