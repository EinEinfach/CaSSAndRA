// The route uploaded to the robot: progress along it.
import type { RobotStatus } from './types.ts';

/** Fraction (0..1) of the route behind the robot. */
export function routeProgress(mowPointIndex: number, routeLength: number): number {
	if (routeLength <= 0) return 0;
	return Math.min(1, Math.max(0, mowPointIndex / routeLength));
}

/** Progress and skipping make sense while the robot follows the route. */
export function followsRoute(status: RobotStatus): boolean {
	return status === 'mow' || status === 'transit';
}
