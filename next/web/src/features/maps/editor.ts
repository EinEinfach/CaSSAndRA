// Editing a map: pure functions on an immutable draft, plus undo history.
import type { Point } from '#shared/viewport.ts';
import type { MapShape } from './types.ts';

/**
 * The map being edited, plus the area drawn to add to the lawn or cut out of
 * it (legacy "figure"). The area is not part of the saved map.
 */
export interface Draft extends MapShape {
	figure?: Point[];
}

/** The lawn: what an area is added to or cut out of. */
export type Lawn = Pick<MapShape, 'perimeter' | 'exclusions'>;

/** The part of the map being edited. */
export type Layer =
	| { kind: 'perimeter' }
	| { kind: 'exclusion'; index: number }
	| { kind: 'dock' }
	| { kind: 'searchWire' }
	| { kind: 'figure' };

export const figureLayer: Layer = { kind: 'figure' };

export const perimeterLayer: Layer = { kind: 'perimeter' };

/** Polygons are closed; dock path and search wire are lines. */
export const isClosed = (layer: Layer) => layer.kind !== 'dock' && layer.kind !== 'searchWire';

export const sameLayer = (a: Layer, b: Layer) =>
	a.kind === b.kind && (a.kind !== 'exclusion' || a.index === (b as typeof a).index);

export function layerName(layer: Layer): string {
	switch (layer.kind) {
		case 'perimeter':
			return 'Perimeter';
		case 'exclusion':
			return `Exclusion ${layer.index + 1}`;
		case 'dock':
			return 'Dock path';
		case 'searchWire':
			return 'Search wire';
		case 'figure':
			return 'Area';
	}
}

export function emptyShape(name = ''): MapShape {
	return { name, perimeter: [], exclusions: [], dock: [], searchWire: [] };
}

export function pointsOf(m: Draft, layer: Layer): Point[] {
	switch (layer.kind) {
		case 'perimeter':
			return m.perimeter;
		case 'exclusion':
			return m.exclusions[layer.index] ?? [];
		case 'dock':
			return m.dock;
		case 'searchWire':
			return m.searchWire;
		case 'figure':
			return m.figure ?? [];
	}
}

export function withPoints(m: Draft, layer: Layer, pts: Point[]): Draft {
	switch (layer.kind) {
		case 'perimeter':
			return { ...m, perimeter: pts };
		case 'exclusion':
			return { ...m, exclusions: m.exclusions.map((e, i) => (i === layer.index ? pts : e)) };
		case 'dock':
			return { ...m, dock: pts };
		case 'searchWire':
			return { ...m, searchWire: pts };
		case 'figure':
			return { ...m, figure: pts };
	}
}

/** Coordinates in centimeter precision, as the robot stores them. */
export const roundPoint = (p: Point): Point => ({
	x: Math.round(p.x * 100) / 100,
	y: Math.round(p.y * 100) / 100
});

/**
 * Adds p to the layer and returns the new map and the index of the new point.
 * Polygons with at least 3 points get the point on their nearest edge, so a
 * click near an edge adds a corner there; lines and new polygons grow at the end.
 */
export function addPoint(m: Draft, layer: Layer, p: Point): { map: Draft; index: number } {
	const pts = pointsOf(m, layer);
	const pt = roundPoint(p);
	let index = pts.length;
	if (isClosed(layer) && pts.length >= 3) {
		let best = Infinity;
		for (let i = 0; i < pts.length; i++) {
			const d = distanceToSegment(pt, pts[i], pts[(i + 1) % pts.length]);
			if (d < best) {
				best = d;
				index = i + 1;
			}
		}
	}
	const next = [...pts.slice(0, index), pt, ...pts.slice(index)];
	return { map: withPoints(m, layer, next), index };
}

export function movePoint(m: Draft, layer: Layer, index: number, p: Point): Draft {
	return withPoints(
		m,
		layer,
		pointsOf(m, layer).map((q, i) => (i === index ? roundPoint(p) : q))
	);
}

export function removePoint(m: Draft, layer: Layer, index: number): Draft {
	return withPoints(
		m,
		layer,
		pointsOf(m, layer).filter((_, i) => i !== index)
	);
}

export function addExclusion(m: Draft): { map: Draft; layer: Layer } {
	return {
		map: { ...m, exclusions: [...m.exclusions, []] },
		layer: { kind: 'exclusion', index: m.exclusions.length }
	};
}

/** Removes an exclusion entirely, or clears any other layer. */
export function clearLayer(m: Draft, layer: Layer): Draft {
	if (layer.kind === 'exclusion') {
		return { ...m, exclusions: m.exclusions.filter((_, i) => i !== layer.index) };
	}
	return withPoints(m, layer, []);
}

export function allLayers(m: Draft): Layer[] {
	return [
		perimeterLayer,
		...m.exclusions.map((_, index): Layer => ({ kind: 'exclusion', index })),
		{ kind: 'dock' },
		{ kind: 'searchWire' },
		figureLayer
	];
}

/** The point within radius of p, preferring the given layer. */
export function hitPoint(
	m: Draft,
	p: Point,
	radius: number,
	prefer?: Layer
): { layer: Layer; index: number } | null {
	const layers = allLayers(m);
	if (prefer) {
		layers.sort((a, b) => Number(sameLayer(b, prefer)) - Number(sameLayer(a, prefer)));
	}
	for (const layer of layers) {
		let best = -1;
		let bestD = radius;
		pointsOf(m, layer).forEach((q, i) => {
			const d = Math.hypot(q.x - p.x, q.y - p.y);
			if (d <= bestD) {
				bestD = d;
				best = i;
			}
		});
		if (best >= 0) return { layer, index: best };
	}
	return null;
}

/** Whether the drawn area can be added or cut out. */
export const figureReady = (m: Draft) => (m.figure ?? []).length >= 3;

/** The draft with a reshaped lawn; the area is used up. */
export function withLawn(m: Draft, lawn: Lawn): Draft {
	return { ...m, perimeter: lawn.perimeter, exclusions: lawn.exclusions, figure: [] };
}

/** The map without the drawn area, as it is saved. */
export function shapeOf(m: Draft): MapShape {
	return {
		name: m.name,
		perimeter: m.perimeter,
		exclusions: m.exclusions,
		dock: m.dock,
		searchWire: m.searchWire
	};
}

export function distanceToSegment(p: Point, a: Point, b: Point): number {
	const dx = b.x - a.x;
	const dy = b.y - a.y;
	const len2 = dx * dx + dy * dy;
	const t = len2 === 0 ? 0 : Math.max(0, Math.min(1, ((p.x - a.x) * dx + (p.y - a.y) * dy) / len2));
	return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

/** What keeps the map from being saved; mirrors maps.Map.Validate. */
export function problems(m: MapShape): string[] {
	const out: string[] = [];
	if (m.name.trim() === '') out.push('Give the map a name.');
	if (m.perimeter.length < 3) out.push('The perimeter needs at least 3 points.');
	m.exclusions.forEach((e, i) => {
		if (e.length < 3) out.push(`Exclusion ${i + 1} needs at least 3 points.`);
	});
	if (m.dock.length === 1) out.push('The dock path needs at least 2 points.');
	if (m.searchWire.length === 1) out.push('The search wire needs at least 2 points.');
	return out;
}

/** Undo/redo over immutable values. */
export class History<T> {
	private past: T[] = [];
	private future: T[] = [];

	constructor(
		public present: T,
		private limit = 200
	) {}

	push(next: T): void {
		this.past.push(this.present);
		if (this.past.length > this.limit) this.past.shift();
		this.present = next;
		this.future = [];
	}

	get canUndo(): boolean {
		return this.past.length > 0;
	}

	get canRedo(): boolean {
		return this.future.length > 0;
	}

	undo(): T {
		const prev = this.past.pop();
		if (prev !== undefined) {
			this.future.push(this.present);
			this.present = prev;
		}
		return this.present;
	}

	redo(): T {
		const next = this.future.pop();
		if (next !== undefined) {
			this.past.push(this.present);
			this.present = next;
		}
		return this.present;
	}
}
