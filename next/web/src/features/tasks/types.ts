// Tasks as sent by the backend (tasks/plan.go, tasks/preview.go, tasks/api.go).
import type { Point } from '#shared/viewport.ts';
import type { Pattern } from '#features/settings/types.ts';

/** How a part of the garden is mowed; the defaults come from the planner settings. */
export interface Parameters {
	pattern: Pattern;
	widthM: number;
	angleDeg: number;
	/** In lane widths. */
	distanceToBorder: number;
	mowArea: boolean;
	borderLaps: number;
	mowExclusions: boolean;
	borderCcw: boolean;
}

export interface PreviewRequest {
	/** A polygon around the part to mow; empty = the whole garden. */
	selection: Point[];
	parameters: Parameters;
}

/** A computed route for the active map. */
export interface Plan {
	mapId: string;
	mapUpdatedAt: string;
	selection: Point[];
	parameters: Parameters;
	start: Point;
	route: Point[];
	distanceM: number;
	createdAt: string;
}

/** The "plan" event and GET /api/tasks/preview. */
export interface PlanEvent {
	plan: Plan | null;
}
