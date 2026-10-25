// Pure helpers for the schedule editor.
import type { Day, Schedule, ScheduleStatus } from './types.ts';

/** "HH:MM" as minutes after midnight. */
export function minutes(hhmm: string): number {
	const [h, m] = hhmm.split(':').map(Number);
	return h * 60 + m;
}

/** Minutes after midnight as "HH:MM". */
export function clock(min: number): string {
	return `${String(Math.floor(min / 60)).padStart(2, '0')}:${String(min % 60).padStart(2, '0')}`;
}

/** The times offered in the editor: every quarter hour from 00:00 to 24:00, plus value if it is off that grid. */
export function timeOptions(value: string): string[] {
	const times = Array.from({ length: 97 }, (_, i) => clock(i * 15));
	if (!times.includes(value)) {
		times.push(value);
		times.sort((a, b) => minutes(a) - minutes(b));
	}
	return times;
}

export function isDayOff(d: Day): boolean {
	return minutes(d.end) <= minutes(d.start);
}

/** Switches a day on (a three-hour window from its start, at most until midnight) or off. */
export function setDayOn(d: Day, on: boolean): Day {
	if (!on) return { ...d, end: d.start };
	const start = minutes(d.start) >= 24 * 60 ? 21 * 60 : minutes(d.start);
	return { ...d, start: clock(start), end: clock(Math.min(start + 180, 24 * 60)) };
}

/** Sets the start and keeps the end, unless the end would come first: then the window keeps its length. */
export function setStart(d: Day, start: string): Day {
	const s = minutes(start);
	let e = minutes(d.end);
	if (e <= s) e = Math.min(s + Math.max(e - minutes(d.start), 15), 24 * 60);
	return { ...d, start, end: clock(e) };
}

export function isDirty(saved: Schedule, draft: Schedule): boolean {
	return JSON.stringify(saved) !== JSON.stringify(draft);
}

const weekdayShort = new Intl.DateTimeFormat('en-GB', { weekday: 'short' });
const time = new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit' });

/** When the next start is, relative to now: "now", "today 09:00", "tomorrow 07:30", "Wed 07:30". */
export function formatNext(next: string, now: Date): string {
	if (!next) return '';
	const at = new Date(next);
	if (at.getTime() <= now.getTime()) return 'now';
	const day = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
	const days = Math.round((day(at) - day(now)) / 86_400_000);
	const when = days === 0 ? 'today' : days === 1 ? 'tomorrow' : weekdayShort.format(at);
	return `${when} ${time.format(at)}`;
}

/** One line about the schedule for the page header. */
export function describe(status: ScheduleStatus, now: Date): string {
	if (status.state === 'off') return 'The schedule is off.';
	const next = formatNext(status.next, now);
	const parts = [];
	if (status.message) parts.push(status.message[0].toUpperCase() + status.message.slice(1) + '.');
	if (next) parts.push(`Next start: ${next}.`);
	else if (!status.message) parts.push('No window planned.');
	return parts.join(' ');
}
