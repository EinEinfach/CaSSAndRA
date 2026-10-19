// Describing a computed route.
import type { Parameters, Plan, PreviewRequest } from './types.ts';

const sameNumbers = (a: { x: number; y: number }[], b: { x: number; y: number }[]) =>
	a.length === b.length && a.every((p, i) => p.x === b[i].x && p.y === b[i].y);

const sameParameters = (a: Parameters, b: Parameters) =>
	(Object.keys(a) as (keyof Parameters)[]).every((k) => a[k] === b[k]);

/** Whether the plan was computed for exactly this request. */
export function planMatches(plan: Plan, req: PreviewRequest): boolean {
	return (
		sameNumbers(plan.selection, req.selection) && sameParameters(plan.parameters, req.parameters)
	);
}

export function formatDistance(m: number): string {
	return m >= 1000 ? `${(m / 1000).toFixed(1)} km` : `${Math.round(m)} m`;
}

/** Driving time at speed, rounded to 5 minutes; turns and transits make it longer. */
export function formatDuration(distanceM: number, speedMps: number): string {
	if (!(speedMps > 0)) return '';
	const min = Math.max(5, Math.round(distanceM / speedMps / 60 / 5) * 5);
	const h = Math.floor(min / 60);
	return h > 0 ? `${h} h ${min % 60} min` : `${min} min`;
}
