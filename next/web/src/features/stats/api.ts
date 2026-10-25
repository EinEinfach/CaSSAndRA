// Stats API (stats/api.go).
import { getJSON } from '#shared/api.ts';
import type { StatsResponse } from './types.ts';

export function fetchStats(
	from: Date,
	to: Date,
	points: number,
	fetchFn: typeof fetch = fetch
): Promise<StatsResponse> {
	const q = new URLSearchParams({
		from: from.toISOString().replace(/\.\d{3}Z$/, 'Z'),
		to: to.toISOString().replace(/\.\d{3}Z$/, 'Z'),
		points: String(points)
	});
	return getJSON<StatsResponse>(`/api/stats?${q}`, fetchFn);
}
