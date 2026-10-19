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

/** One piece of a task: what to mow and how. */
export interface Part {
	/** A polygon around the part to mow; empty = the whole garden. */
	selection: Point[];
	parameters: Parameters;
}

/** A saved mowing job of one map; its parts are mowed one after another. */
export interface Task {
	id: string;
	name: string;
	mapId: string;
	parts: Part[];
	updatedAt: string;
}

/** The editable part of a task. */
export type TaskShape = Pick<Task, 'name' | 'mapId' | 'parts'>;

/** Either drawn parts or saved tasks, mowed in the given order. */
export interface PreviewRequest {
	parts?: Part[];
	taskIds?: string[];
}

/** A computed route for the active map. */
export interface Plan {
	mapId: string;
	mapUpdatedAt: string;
	/** The saved tasks the route was planned for; empty for drawn parts. */
	taskIds: string[];
	parts: Part[];
	start: Point;
	route: Point[];
	distanceM: number;
	createdAt: string;
}

/** The "plan" event and GET /api/tasks/preview. */
export interface PlanEvent {
	plan: Plan | null;
}

/** The "tasks" event and GET /api/tasks. */
export interface TaskList {
	tasks: Task[];
}
