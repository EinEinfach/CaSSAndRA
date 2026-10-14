// The path the robot drove recently, for drawing behind it.
import type { Point } from '#shared/viewport.ts';

export interface TrailOptions {
	/** Oldest points are dropped beyond this length. */
	maxPoints: number;
	/** Points closer than this to the last one are skipped (GPS noise, standstill). */
	minDistanceM: number;
	/** A jump longer than this starts a new trail (relocated or kidnapped robot). */
	maxJumpM: number;
}

export const defaultTrailOptions: TrailOptions = {
	maxPoints: 2000,
	minDistanceM: 0.05,
	maxJumpM: 5
};

/** Returns the trail with p appended. The input is not modified. */
export function extendTrail(
	trail: Point[],
	p: Point,
	opts: TrailOptions = defaultTrailOptions
): Point[] {
	const last = trail[trail.length - 1];
	if (last) {
		const d = Math.hypot(p.x - last.x, p.y - last.y);
		if (d < opts.minDistanceM) return trail;
		if (d > opts.maxJumpM) return [p];
	}
	const next = [...trail, p];
	return next.length > opts.maxPoints ? next.slice(next.length - opts.maxPoints) : next;
}
