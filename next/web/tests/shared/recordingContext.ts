// A fake 2D canvas context that records what is drawn, for tests.
import type { MapContext } from '#shared/drawMap.ts';

export interface Shape {
	/** fill or stroke */
	op: 'fill' | 'stroke';
	color: string;
	points: [number, number][];
	closed: boolean;
	dashed: boolean;
	arcs: [number, number, number][];
}

export function recordingContext(): MapContext & { shapes: Shape[]; rects: string[] } {
	let points: [number, number][] = [];
	let arcs: [number, number, number][] = [];
	let closed = false;
	let dashed = false;
	const shapes: Shape[] = [];
	const rects: string[] = [];
	const ctx = {
		shapes,
		rects,
		fillStyle: '' as MapContext['fillStyle'],
		strokeStyle: '' as MapContext['strokeStyle'],
		lineWidth: 1,
		lineJoin: 'miter' as CanvasLineJoin,
		lineCap: 'butt' as CanvasLineCap,
		beginPath() {
			points = [];
			arcs = [];
			closed = false;
		},
		moveTo(x: number, y: number) {
			points.push([x, y]);
		},
		lineTo(x: number, y: number) {
			points.push([x, y]);
		},
		closePath() {
			closed = true;
		},
		arc(x: number, y: number, r: number) {
			arcs.push([x, y, r]);
		},
		fill() {
			shapes.push({ op: 'fill', color: String(ctx.fillStyle), points, closed, dashed, arcs });
		},
		stroke() {
			shapes.push({ op: 'stroke', color: String(ctx.strokeStyle), points, closed, dashed, arcs });
		},
		fillRect() {
			rects.push(String(ctx.fillStyle));
		},
		setLineDash(d: number[]) {
			dashed = d.length > 0;
		},
		save() {},
		restore() {},
		translate() {},
		rotate() {}
	};
	return ctx as unknown as MapContext & { shapes: Shape[]; rects: string[] };
}
