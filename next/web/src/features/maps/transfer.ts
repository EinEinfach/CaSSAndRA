// Maps from and to files, compatible with legacy CaSSAndRA: the export of the
// Sunray app (several maps, meters) and GeoJSON (one map, longitude/latitude).
import type { Point } from '#shared/viewport.ts';
import { roundPoint } from './editor.ts';
import type { MapShape } from './types.ts';

/** Where the robot's coordinate system has its (0, 0): Settings → Rover. */
export interface Origin {
	lon: number;
	lat: number;
}

/** Meters per degree of latitude, as legacy CaSSAndRA and Sunray use it. */
const M_PER_DEG = 111111;

const lonScale = (o: Origin) => M_PER_DEG * Math.cos((o.lat * Math.PI) / 180);

export function toLonLat(p: Point, o: Origin): [number, number] {
	return [p.x / lonScale(o) + o.lon, p.y / M_PER_DEG + o.lat];
}

export function fromLonLat([lon, lat]: [number, number], o: Origin): Point {
	return roundPoint({ x: (lon - o.lon) * lonScale(o), y: (lat - o.lat) * M_PER_DEG });
}

const isNumber = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
const isObject = (v: unknown): v is Record<string, unknown> =>
	typeof v === 'object' && v !== null && !Array.isArray(v);

/** Files close their rings (last point = first), maps do not. */
function openRing(pts: Point[]): Point[] {
	const [first, last] = [pts[0], pts.at(-1)];
	return pts.length > 1 && first.x === last!.x && first.y === last!.y ? pts.slice(0, -1) : pts;
}

// --- Sunray app export ---------------------------------------------------

/** Points as the Sunray app stores them: {"X": 1.2, "Y": 3.4, …}. */
function sunrayPoints(v: unknown, what: string): Point[] {
	if (v === undefined || v === null) return [];
	if (!Array.isArray(v)) throw new Error(`${what} is not a list of points`);
	return v.map((p) => {
		if (!isObject(p) || !isNumber(p.X) || !isNumber(p.Y)) {
			throw new Error(`${what} has a point without X and Y`);
		}
		return roundPoint({ x: p.X, y: p.Y });
	});
}

/** The used slots of a Sunray export; empty slots are skipped. */
function fromSunray(slots: unknown[], baseName: string): MapShape[] {
	const maps: MapShape[] = [];
	slots.forEach((slot, i) => {
		if (!isObject(slot)) return;
		const what = `map ${i + 1}`;
		const perimeter = openRing(sunrayPoints(slot.perimeter, `the perimeter of ${what}`));
		if (perimeter.length < 3) return;
		const exclusions = Array.isArray(slot.exclusions) ? slot.exclusions : [];
		maps.push({
			name: `${baseName} ${i + 1}`,
			perimeter,
			exclusions: exclusions
				.map((e, j) => openRing(sunrayPoints(e, `exclusion ${j + 1} of ${what}`)))
				.filter((e) => e.length >= 3),
			dock: sunrayPoints(slot.dockpoints, `the dock path of ${what}`),
			searchWire: []
		});
	});
	return maps;
}

// --- GeoJSON ---------------------------------------------------------------

function lonLats(v: unknown, what: string, o: Origin): Point[] {
	if (!Array.isArray(v)) throw new Error(`${what} has no coordinates`);
	return v.map((c) => {
		if (!Array.isArray(c) || !isNumber(c[0]) || !isNumber(c[1])) {
			throw new Error(`${what} has a coordinate that is not [longitude, latitude]`);
		}
		return fromLonLat([c[0], c[1]], o);
	});
}

function fromGeoJSON(doc: Record<string, unknown>, name: string, o: Origin): MapShape {
	const map: MapShape = { name, perimeter: [], exclusions: [], dock: [], searchWire: [] };
	const features = Array.isArray(doc.features) ? doc.features : [];
	for (const f of features) {
		if (!isObject(f) || !isObject(f.properties) || !isObject(f.geometry)) continue;
		const kind = f.properties.name;
		const coords = f.geometry.coordinates;
		// Polygons list rings; the first is the outline.
		const ring = (what: string) =>
			openRing(lonLats(Array.isArray(coords) ? coords[0] : undefined, what, o));
		if (kind === 'perimeter') map.perimeter = ring('the perimeter');
		else if (kind === 'exclusion') map.exclusions.push(ring('an exclusion'));
		else if (kind === 'dockpoints') map.dock = lonLats(coords, 'the dock path', o);
		else if (kind === 'search wire') map.searchWire = lonLats(coords, 'the search wire', o);
	}
	if (map.perimeter.length < 3) throw new Error('the file has no perimeter');
	map.exclusions = map.exclusions.filter((e) => e.length >= 3);
	return map;
}

/** The file name without folder and extension, as a start for the map name. */
export function baseName(fileName: string): string {
	return (
		fileName
			.replace(/^.*[\\/]/, '')
			.replace(/\.[^.]*$/, '')
			.trim() || 'Imported map'
	);
}

/**
 * Reads the maps of a Sunray export or the one map of a GeoJSON file. Nothing
 * is saved: the maps go to the editor. Throws an Error that says what is wrong.
 */
export function importMaps(text: string, fileName: string, origin: Origin): MapShape[] {
	let doc: unknown;
	try {
		doc = JSON.parse(text);
	} catch {
		throw new Error('The file is not JSON.');
	}
	const name = baseName(fileName);
	let maps: MapShape[];
	try {
		if (Array.isArray(doc)) maps = fromSunray(doc, name);
		else if (isObject(doc) && doc.type === 'FeatureCollection') {
			maps = [fromGeoJSON(doc, name, origin)];
		} else throw new Error('it is neither a Sunray export nor GeoJSON');
	} catch (err) {
		throw new Error(`Cannot import: ${(err as Error).message}.`, { cause: err });
	}
	if (maps.length === 0) throw new Error('Cannot import: the file has no map with a perimeter.');
	return maps;
}

/** The map as GeoJSON like legacy CaSSAndRA exports it (rings closed, [lon, lat]). */
export function exportGeoJSON(map: MapShape, origin: Origin): string {
	const line = (pts: Point[]) => pts.map((p) => toLonLat(p, origin));
	const ring = (pts: Point[]) => [line(pts.length > 0 ? [...pts, pts[0]] : [])];
	const feature = (name: string, type: string, coordinates: unknown, extra = {}) => ({
		type: 'Feature',
		properties: { name },
		...extra,
		geometry: { type, coordinates }
	});
	return JSON.stringify({
		type: 'FeatureCollection',
		features: [
			feature('perimeter', 'Polygon', ring(map.perimeter)),
			feature('dockpoints', 'LineString', line(map.dock)),
			feature('search wire', 'LineString', line(map.searchWire)),
			...map.exclusions.map((e, idx) => feature('exclusion', 'Polygon', ring(e), { idx }))
		]
	});
}

/** A file name that every system accepts. */
export function exportFileName(mapName: string): string {
	const safe = mapName.trim().replace(/[^\p{L}\p{N} ._-]+/gu, '_') || 'map';
	return `${safe}.geojson`;
}

/** Offers text as a file download. */
export function downloadText(fileName: string, text: string, doc: Document = document): void {
	const url = URL.createObjectURL(new Blob([text], { type: 'application/geo+json' }));
	const a = doc.createElement('a');
	a.href = url;
	a.download = fileName;
	doc.body.append(a);
	a.click();
	a.remove();
	URL.revokeObjectURL(url);
}
