// Maps API (maps/api.go).
import { getJSON, sendJSON } from '#shared/api.ts';
import type { GardenMap, MapList, MapShape } from './types.ts';

export const fetchMaps = (fetchFn: typeof fetch = fetch) => getJSON<MapList>('/api/maps', fetchFn);

export async function createMap(m: MapShape, fetchFn: typeof fetch = fetch): Promise<GardenMap> {
	return (await sendJSON<GardenMap>('POST', '/api/maps', m, fetchFn))!;
}

export async function updateMap(
	id: string,
	m: MapShape,
	fetchFn: typeof fetch = fetch
): Promise<GardenMap> {
	return (await sendJSON<GardenMap>('PUT', `/api/maps/${encodeURIComponent(id)}`, m, fetchFn))!;
}

export async function deleteMap(id: string, fetchFn: typeof fetch = fetch): Promise<void> {
	await sendJSON('DELETE', `/api/maps/${encodeURIComponent(id)}`, undefined, fetchFn);
}

/** Makes the map active ("" = none) without sending it to the robot. */
export async function activateMap(id: string, fetchFn: typeof fetch = fetch): Promise<void> {
	await sendJSON('PUT', '/api/maps/active', { id }, fetchFn);
}

/** Sends the map to the robot and makes it active. */
export async function uploadMap(id: string, fetchFn: typeof fetch = fetch): Promise<void> {
	await sendJSON('POST', `/api/maps/${encodeURIComponent(id)}/upload`, undefined, fetchFn);
}
