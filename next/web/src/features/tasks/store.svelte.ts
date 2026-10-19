// The saved tasks and the planned route for the UI, kept current by the
// "tasks" and "plan" events.
import type { EventStream } from '#shared/events.ts';
import type { Plan, PlanEvent, Task, TaskList } from './types.ts';

export class PlanStore {
	plan = $state.raw<Plan | null>(null);
	/** False until the first event arrived. */
	loaded = $state(false);

	/** Starts following the stream. Returns a function that stops it. */
	connect(stream: EventStream): () => void {
		return stream.on<PlanEvent>('plan', (e) => this.apply(e));
	}

	apply(e: PlanEvent): void {
		this.plan = e.plan;
		this.loaded = true;
	}
}

export class TaskStore {
	tasks = $state.raw<Task[]>([]);
	loaded = $state(false);

	connect(stream: EventStream): () => void {
		return stream.on<TaskList>('tasks', (l) => this.apply(l));
	}

	apply(l: TaskList): void {
		this.tasks = l.tasks;
		this.loaded = true;
	}

	/** The tasks of a map, sorted by name as the backend sends them. */
	forMap(mapId: string | undefined): Task[] {
		return this.tasks.filter((t) => t.mapId === mapId);
	}
}
