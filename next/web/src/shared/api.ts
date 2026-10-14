// Client for the CaSSAndRA HTTP API.

export interface Health {
	status: string;
	version: string;
}

export class ApiError extends Error {
	constructor(
		readonly path: string,
		readonly status: number,
		detail?: string
	) {
		super(detail ? `${path}: ${detail}` : `${path} failed with status ${status}`);
		this.name = 'ApiError';
	}
}

/** Reads the {"error": "..."} body the backend sends with failures. */
async function errorDetail(res: Response): Promise<string | undefined> {
	try {
		const body = (await res.json()) as { error?: unknown };
		return typeof body.error === 'string' ? body.error : undefined;
	} catch {
		return undefined;
	}
}

export async function getJSON<T>(path: string, fetchFn: typeof fetch = fetch): Promise<T> {
	const res = await fetchFn(path, { headers: { Accept: 'application/json' } });
	if (!res.ok) {
		throw new ApiError(path, res.status, await errorDetail(res));
	}
	return (await res.json()) as T;
}

/** Sends a command. The backend answers 204 without body on success. */
export async function post(
	path: string,
	body?: unknown,
	fetchFn: typeof fetch = fetch
): Promise<void> {
	const res = await fetchFn(path, {
		method: 'POST',
		headers: body === undefined ? {} : { 'Content-Type': 'application/json' },
		body: body === undefined ? undefined : JSON.stringify(body)
	});
	if (!res.ok) {
		throw new ApiError(path, res.status, await errorDetail(res));
	}
}

export function fetchHealth(fetchFn: typeof fetch = fetch): Promise<Health> {
	return getJSON<Health>('/api/health', fetchFn);
}
