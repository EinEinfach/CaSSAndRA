// The schedule and its status for the UI, kept current by the "schedule" event.
import type { EventStream } from '#shared/events.ts';
import type { ScheduleView } from './types.ts';

export class ScheduleStore {
	view = $state.raw<ScheduleView | null>(null);

	connect(stream: EventStream): () => void {
		return stream.on<ScheduleView>('schedule', (v) => this.apply(v));
	}

	apply(v: ScheduleView): void {
		this.view = v;
	}
}
