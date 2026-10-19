// Choosing the part of the garden to mow: pure geometry helpers.
import type { Point } from '#shared/viewport.ts';

/** Whole garden, a rectangle dragged on the map, or a polygon of tapped corners. */
export type Tool = 'all' | 'rectangle' | 'polygon';

/** Selections smaller than this (m²) are taken as a slip, not a choice. */
export const MIN_AREA_M2 = 0.25;

/** Coordinates in centimeter precision, as maps store them. */
export const roundPoint = (p: Point): Point => ({
	x: Math.round(p.x * 100) / 100,
	y: Math.round(p.y * 100) / 100
});

/** The rectangle with corners a and c, counter-clockwise. */
export function rectangle(a: Point, c: Point): Point[] {
	const [x0, x1] = [Math.min(a.x, c.x), Math.max(a.x, c.x)];
	const [y0, y1] = [Math.min(a.y, c.y), Math.max(a.y, c.y)];
	return [
		{ x: x0, y: y0 },
		{ x: x1, y: y0 },
		{ x: x1, y: y1 },
		{ x: x0, y: y1 }
	].map(roundPoint);
}

/** Area of a polygon (shoelace), always positive. */
export function area(pts: Point[]): number {
	let sum = 0;
	pts.forEach((p, i) => {
		const q = pts[(i + 1) % pts.length];
		sum += p.x * q.y - q.x * p.y;
	});
	return Math.abs(sum) / 2;
}

/** Whether pts can be sent as a selection. */
export const isUsable = (pts: Point[]) => pts.length >= 3 && area(pts) >= MIN_AREA_M2;

/** Index of the point within radius of p, or -1. */
export function hit(pts: Point[], p: Point, radius: number): number {
	let best = -1;
	let bestD = radius;
	pts.forEach((q, i) => {
		const d = Math.hypot(q.x - p.x, q.y - p.y);
		if (d <= bestD) {
			best = i;
			bestD = d;
		}
	});
	return best;
}
