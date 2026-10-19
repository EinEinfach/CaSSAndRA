// Tasks API (tasks/api.go).
import { sendJSON } from '#shared/api.ts';
import type { Plan, PreviewRequest, Task, TaskShape } from './types.ts';

/** Computes the route and makes it the plan every browser shows. */
export async function previewRoute(
	req: PreviewRequest,
	fetchFn: typeof fetch = fetch
): Promise<Plan> {
	return (await sendJSON<Plan>('POST', '/api/tasks/preview', req, fetchFn))!;
}

export async function clearPreview(fetchFn: typeof fetch = fetch): Promise<void> {
	await sendJSON('DELETE', '/api/tasks/preview', undefined, fetchFn);
}

/** Sends the planned route to the robot and starts mowing. */
export async function startMowing(fetchFn: typeof fetch = fetch): Promise<void> {
	await sendJSON('POST', '/api/tasks/start', undefined, fetchFn);
}

export async function createTask(t: TaskShape, fetchFn: typeof fetch = fetch): Promise<Task> {
	return (await sendJSON<Task>('POST', '/api/tasks', t, fetchFn))!;
}

export async function updateTask(
	id: string,
	t: TaskShape,
	fetchFn: typeof fetch = fetch
): Promise<Task> {
	return (await sendJSON<Task>('PUT', `/api/tasks/${encodeURIComponent(id)}`, t, fetchFn))!;
}

export async function deleteTask(id: string, fetchFn: typeof fetch = fetch): Promise<void> {
	await sendJSON('DELETE', `/api/tasks/${encodeURIComponent(id)}`, undefined, fetchFn);
}
