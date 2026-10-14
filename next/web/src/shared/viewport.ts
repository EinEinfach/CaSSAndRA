// Mapping between world coordinates (meters, y up) and canvas pixels (y down).

export interface Point {
	x: number;
	y: number;
}

/** screen = (world - center) * scale, flipped in y, moved to the canvas middle. */
export interface Viewport {
	centerX: number;
	centerY: number;
	/** pixels per meter */
	scale: number;
	width: number;
	height: number;
}

export const MIN_SCALE = 0.5;
export const MAX_SCALE = 500;

const clampScale = (s: number) => Math.min(MAX_SCALE, Math.max(MIN_SCALE, s));

/** Shows all points with padding pixels around them. */
export function fit(points: Point[], width: number, height: number, padding = 24): Viewport {
	if (points.length === 0) {
		return { centerX: 0, centerY: 0, scale: 20, width, height };
	}
	let minX = Infinity,
		minY = Infinity,
		maxX = -Infinity,
		maxY = -Infinity;
	for (const p of points) {
		minX = Math.min(minX, p.x);
		maxX = Math.max(maxX, p.x);
		minY = Math.min(minY, p.y);
		maxY = Math.max(maxY, p.y);
	}
	const spanX = Math.max(maxX - minX, 1);
	const spanY = Math.max(maxY - minY, 1);
	const usableW = Math.max(width - 2 * padding, 1);
	const usableH = Math.max(height - 2 * padding, 1);
	return {
		centerX: (minX + maxX) / 2,
		centerY: (minY + maxY) / 2,
		scale: clampScale(Math.min(usableW / spanX, usableH / spanY)),
		width,
		height
	};
}

export function toScreen(vp: Viewport, p: Point): Point {
	return {
		x: vp.width / 2 + (p.x - vp.centerX) * vp.scale,
		y: vp.height / 2 - (p.y - vp.centerY) * vp.scale
	};
}

export function toWorld(vp: Viewport, s: Point): Point {
	return {
		x: vp.centerX + (s.x - vp.width / 2) / vp.scale,
		y: vp.centerY - (s.y - vp.height / 2) / vp.scale
	};
}

/** Zooms by factor while keeping the world point under the screen point in place. */
export function zoomAt(vp: Viewport, factor: number, screen: Point): Viewport {
	const anchor = toWorld(vp, screen);
	const scale = clampScale(vp.scale * factor);
	return {
		...vp,
		scale,
		centerX: anchor.x - (screen.x - vp.width / 2) / scale,
		centerY: anchor.y + (screen.y - vp.height / 2) / scale
	};
}

/** Moves the view by a drag of dx/dy pixels. */
export function pan(vp: Viewport, dx: number, dy: number): Viewport {
	return { ...vp, centerX: vp.centerX - dx / vp.scale, centerY: vp.centerY + dy / vp.scale };
}

/** Keeps the world center when the canvas changes size. */
export function resize(vp: Viewport, width: number, height: number): Viewport {
	return { ...vp, width, height };
}
