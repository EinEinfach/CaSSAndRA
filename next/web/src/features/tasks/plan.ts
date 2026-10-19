// Describing a computed route.
import type { RobotStatus } from '#features/robot/types.ts';
import type { Parameters, Part, Plan } from './types.ts';

/** A route can be sent while the robot stands still: idle or in the dock. */
export function canStartRoute(status: RobotStatus): boolean {
	return status === 'idle' || status === 'docked' || status === 'charging';
}

const sameNumbers = (a: { x: number; y: number }[], b: { x: number; y: number }[]) =>
	a.length === b.length && a.every((p, i) => p.x === b[i].x && p.y === b[i].y);

const sameParameters = (a: Parameters, b: Parameters) =>
	(Object.keys(a) as (keyof Parameters)[]).every((k) => a[k] === b[k]);

/** Whether the plan was computed for exactly these drawn parts. */
export function planMatchesParts(plan: Plan, parts: Part[]): boolean {
	return (
		plan.taskIds.length === 0 &&
		plan.parts.length === parts.length &&
		plan.parts.every(
			(p, i) =>
				sameNumbers(p.selection, parts[i].selection) &&
				sameParameters(p.parameters, parts[i].parameters)
		)
	);
}

/** Whether the plan was computed for these saved tasks, in this order. */
export function planMatchesTasks(plan: Plan, taskIds: string[]): boolean {
	return plan.taskIds.length === taskIds.length && plan.taskIds.every((id, i) => id === taskIds[i]);
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
