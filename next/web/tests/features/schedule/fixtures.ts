import type { Day, Schedule, ScheduleView } from '#features/schedule/types.ts';

export const dayOff = (): Day => ({ start: '12:00', end: '12:00', taskIds: [] });

export function schedule(overrides: Partial<Schedule> = {}): Schedule {
	return {
		active: true,
		days: [
			{ start: '09:00', end: '12:00', taskIds: ['t1', 't2'] },
			...Array.from({ length: 6 }, dayOff)
		],
		...overrides
	};
}

export function view(overrides: Partial<ScheduleView> = {}): ScheduleView {
	return {
		schedule: schedule(),
		status: { state: 'waiting', message: '', next: '2026-10-26T09:00:00+01:00' },
		...overrides
	};
}
