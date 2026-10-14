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
	robotOutline: 'outline'
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

	it('does not draw a trail of one point', () => {
		const ctx = recordingContext();
		drawMap(ctx, vp, { trail: [{ x: 0, y: 0 }] }, colors);
		expect(ctx.shapes).toEqual([]);
	});
});

describe('mapPoints', () => {
	it('collects everything the view should show', () => {
		expect(
			mapPoints({
				perimeter: [{ x: 0, y: 0 }],
				exclusions: [[{ x: 1, y: 1 }]],
				dock: [{ x: 2, y: 2 }],
				way: [{ x: 3, y: 3 }],
				trail: [{ x: 9, y: 9 }],
				robot: { position: { x: 4, y: 4 }, headingRad: 0 }
			}).map((p) => p.x)
		).toEqual([0, 1, 2, 3, 4]);
	});
});
