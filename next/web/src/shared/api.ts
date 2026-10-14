// Client for the CaSSAndRA HTTP API.

export interface Health {
	status: string;
	version: string;
}

export class ApiError extends Error {
	constructor(
		readonly path: string,
		readonly status: number
	) {
		super(`GET ${path} failed with status ${status}`);
		this.name = 'ApiError';
	}
}

async function getJSON<T>(path: string, fetchFn: typeof fetch): Promise<T> {
	const res = await fetchFn(path, { headers: { Accept: 'application/json' } });
	if (!res.ok) {
		throw new ApiError(path, res.status);
	}
	return (await res.json()) as T;
}

export function fetchHealth(fetchFn: typeof fetch = fetch): Promise<Health> {
	return getJSON<Health>('/api/health', fetchFn);
}
