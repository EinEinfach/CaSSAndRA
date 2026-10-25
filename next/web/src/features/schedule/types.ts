// Types of the schedule API (schedule/api.go).

/** One weekday: a window in local time ("HH:MM", end up to "24:00"); start = end is a day off. */
export interface Day {
	start: string;
	end: string;
	/** Mowed in this order; none means the robot continues its route. */
	taskIds: string[];
}

export interface Schedule {
	active: boolean;
	/** Monday first. */
	days: Day[];
}

export type ScheduleState = 'off' | 'waiting' | 'started' | 'done' | 'failed';

export interface ScheduleStatus {
	state: ScheduleState;
	message: string;
	/** Next start (RFC 3339), empty if none. */
	next: string;
}

/** GET /api/schedule and the "schedule" event. */
export interface ScheduleView {
	schedule: Schedule;
	status: ScheduleStatus;
}

export const weekdays = [
	'Monday',
	'Tuesday',
	'Wednesday',
	'Thursday',
	'Friday',
	'Saturday',
	'Sunday'
] as const;
