// The planned route for the UI, kept current by the "plan" event.
import type { EventStream } from '#shared/events.ts';
import type { Plan, PlanEvent } from './types.ts';

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
