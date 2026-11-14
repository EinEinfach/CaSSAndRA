// Log view API: the app's log, typed robot commands and the computer's load.
import { getJSON, sendJSON } from '#shared/api.ts';
import type { LogEntry, LogList, SystemInfo } from './types.ts';

/** The log records after seq (0 = all the app still keeps). */
export async function fetchLogs(after: number, fetchFn: typeof fetch = fetch): Promise<LogEntry[]> {
	const list = await getJSON<LogList>(`/api/logs?after=${after}`, fetchFn);
	return list.entries;
}

/** Sends one AT+ command to the robot, once, and returns its reply. */
export async function sendCommand(line: string, fetchFn: typeof fetch = fetch): Promise<string> {
	const res = await sendJSON<{ reply: string }>('POST', '/api/robot/raw', { line }, fetchFn);
	return res?.reply ?? '';
}

export function fetchSystem(fetchFn: typeof fetch = fetch): Promise<SystemInfo> {
	return getJSON<SystemInfo>('/api/system', fetchFn);
}
