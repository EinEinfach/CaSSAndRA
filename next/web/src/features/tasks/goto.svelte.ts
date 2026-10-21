// Picking a point on the live map for the robot to drive to. Nothing is sent
// until the user confirms: a tap alone never moves the robot.
import type { MapInteraction } from '#shared/MapCanvas.svelte';
import type { Point } from '#shared/viewport.ts';
import { roundPoint } from './selection.ts';

export class GotoPicker {
	picking = $state(false);
	goal = $state.raw<Point | null>(null);

	start(): void {
		this.picking = true;
		this.goal = null;
	}

	cancel(): void {
		this.picking = false;
		this.goal = null;
	}

	/** For MapCanvas while picking: a tap (re)places the goal, dragging pans. */
	readonly interact: MapInteraction = {
		tap: (p) => {
			if (this.picking) this.goal = roundPoint(p);
		}
	};
}
