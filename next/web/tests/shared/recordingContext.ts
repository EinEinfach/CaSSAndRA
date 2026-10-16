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

export interface Image {
	image: CanvasImageSource;
	/** x, y, width, height relative to the translated origin */
	box: [number, number, number, number];
	at: [number, number];
	rotation: number;
}

type Recording = MapContext & { shapes: Shape[]; rects: string[]; images: Image[] };

export function recordingContext(): Recording {
	let points: [number, number][] = [];
	let arcs: [number, number, number][] = [];
	let closed = false;
	let dashed = false;
	const shapes: Shape[] = [];
	const rects: string[] = [];
	const images: Image[] = [];
	let at: [number, number] = [0, 0];
	let rotation = 0;
	const ctx = {
		shapes,
		rects,
		images,
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
		restore() {
			at = [0, 0];
			rotation = 0;
		},
		translate(x: number, y: number) {
			at = [x, y];
		},
		rotate(angle: number) {
			rotation = angle;
		},
		drawImage(image: CanvasImageSource, x: number, y: number, w: number, h: number) {
			images.push({ image, box: [x, y, w, h], at, rotation });
		}
	};
	return ctx as unknown as Recording;
}
