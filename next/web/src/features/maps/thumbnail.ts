// SVG paths for a small map preview (y up in the world, down in SVG).
import type { Point } from '#shared/viewport.ts';
import type { MapShape } from './types.ts';

export interface Thumbnail {
	perimeter: string;
	exclusions: string[];
	dock: string;
}

/** Fits the map into a size x size square with padding on each side. */
export function thumbnail(m: MapShape, size: number, padding = 4): Thumbnail {
	const all = [...m.perimeter, ...m.exclusions.flat(), ...m.dock];
	if (all.length === 0) return { perimeter: '', exclusions: [], dock: '' };
	const xs = all.map((p) => p.x);
	const ys = all.map((p) => p.y);
	const minX = Math.min(...xs);
	const maxY = Math.max(...ys);
	const span = Math.max(Math.max(...xs) - minX, maxY - Math.min(...ys), 1e-9);
	const scale = (size - 2 * padding) / span;
	const offX = (size - (Math.max(...xs) - minX) * scale) / 2;
	const offY = (size - (maxY - Math.min(...ys)) * scale) / 2;
	const fmt = (v: number) => Number(v.toFixed(1));
	const path = (pts: Point[], closed: boolean) =>
		pts.length === 0
			? ''
			: pts
					.map(
						(p, i) =>
							`${i === 0 ? 'M' : 'L'}${fmt(offX + (p.x - minX) * scale)} ${fmt(offY + (maxY - p.y) * scale)}`
					)
					.join(' ') + (closed ? ' Z' : '');
	return {
		perimeter: path(m.perimeter, true),
		exclusions: m.exclusions.map((e) => path(e, true)),
		dock: path(m.dock, false)
	};
}
