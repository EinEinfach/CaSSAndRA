// Schedule API (schedule/api.go).
import { sendJSON } from '#shared/api.ts';
import type { Schedule, ScheduleView } from './types.ts';

export async function saveSchedule(
	schedule: Schedule,
	fetchFn: typeof fetch = fetch
): Promise<ScheduleView> {
	return (await sendJSON<ScheduleView>('PUT', '/api/schedule', { schedule }, fetchFn))!;
}
