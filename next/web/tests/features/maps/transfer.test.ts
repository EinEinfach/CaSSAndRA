import { describe, expect, it, vi } from 'vitest';
import {
	baseName,
	downloadText,
	exportFileName,
	exportGeoJSON,
	fromLonLat,
	importMaps,
	toLonLat
} from '#features/maps/transfer.ts';
import { garden, pts } from './fixtures.ts';

const origin = { lon: 9, lat: 52 };

// As the Sunray app exports: ten slots, each a map or empty, points with extras.
const sunray = JSON.stringify([
	{
		perimeter: [
			{ X: 0, Y: 0, delta: 0.1, timestamp: 1, sol: 2 },
			{ X: 10.004, Y: 0, delta: 0.1, timestamp: 2, sol: 2 },
			{ X: 10, Y: 10 },
			{ X: 0, Y: 0 }
		],
		exclusions: [
			[
				{ X: 2, Y: 2 },
				{ X: 3, Y: 2 },
				{ X: 3, Y: 3 }
			],
			[{ X: 5, Y: 5 }]
		],
		dockpoints: [
			{ X: 1, Y: 1 },
			{ X: 1, Y: -1 }
		],
		mowpoints: [{ X: 4, Y: 4 }]
	},
	null,
	{ perimeter: [], exclusions: [], dockpoints: [] },
	{
		perimeter: [
			{ X: 0, Y: 0 },
			{ X: 4, Y: 0 },
			{ X: 4, Y: 4 }
		]
	}
]);

describe('coordinates', () => {
	// Expected values from the legacy formula (coords_rel_to_abs), computed by hand.
	it('converts meters to longitude and latitude like legacy', () => {
		const [lon, lat] = toLonLat({ x: 10, y: 5 }, origin);
		expect(lon).toBeCloseTo(9.000146184378277, 12);
		expect(lat).toBeCloseTo(52.000045000045, 12);
	});

	it('converts back, rounded to centimeters', () => {
		expect(fromLonLat([9.0002, 52.0001], origin)).toEqual({ x: 13.68, y: 11.11 });
	});
});

describe('importMaps', () => {
	it('reads the used slots of a Sunray export', () => {
		const maps = importMaps(sunray, '/home/me/sunray maps.json', origin);
		expect(maps).toEqual([
			{
				name: 'sunray maps 1',
				perimeter: pts(0, 0, 10, 0, 10, 10), // rounded, ring opened
				exclusions: [pts(2, 2, 3, 2, 3, 3)], // the single point is no exclusion
				dock: pts(1, 1, 1, -1),
				searchWire: []
			},
			{
				name: 'sunray maps 4',
				perimeter: pts(0, 0, 4, 0, 4, 4),
				exclusions: [],
				dock: [],
				searchWire: []
			}
		]);
	});

	it('reads back what it exported', () => {
		const g = garden();
		const shape = { ...g, searchWire: pts(1, 1, 9, 1) };
		const [back] = importMaps(exportGeoJSON(shape, origin), 'Garden.geojson', origin);
		expect(back).toEqual({
			name: 'Garden',
			perimeter: g.perimeter,
			exclusions: g.exclusions,
			dock: g.dock,
			searchWire: shape.searchWire
		});
	});

	it.each([
		['not json', 'The file is not JSON.'],
		['{"type":"Feature"}', 'Cannot import: it is neither a Sunray export nor GeoJSON.'],
		['[null, {"perimeter": []}]', 'Cannot import: the file has no map with a perimeter.'],
		[
			'[{"perimeter": [{"X": 1}]}]',
			'Cannot import: the perimeter of map 1 has a point without X and Y.'
		],
		['[{"perimeter": 5}]', 'Cannot import: the perimeter of map 1 is not a list of points.'],
		['{"type":"FeatureCollection","features":[]}', 'Cannot import: the file has no perimeter.'],
		[
			'{"type":"FeatureCollection","features":[{"properties":{"name":"perimeter"},"geometry":{"coordinates":[[["a",1]]]}}]}',
			'Cannot import: the perimeter has a coordinate that is not [longitude, latitude].'
		]
	])('explains what is wrong with %s', (text, message) => {
		expect(() => importMaps(text, 'x.json', origin)).toThrow(message);
	});
});

describe('exportGeoJSON', () => {
	it('writes the legacy layout: closed rings, named features, idx on exclusions', () => {
		const doc = JSON.parse(exportGeoJSON(garden(), origin));
		expect(doc.type).toBe('FeatureCollection');
		expect(doc.features.map((f: { properties: { name: string } }) => f.properties.name)).toEqual([
			'perimeter',
			'dockpoints',
			'search wire',
			'exclusion'
		]);
		const [perimeter, dock, wire, exclusion] = doc.features;
		expect(perimeter.geometry.type).toBe('Polygon');
		expect(perimeter.geometry.coordinates[0]).toHaveLength(5);
		expect(perimeter.geometry.coordinates[0][4]).toEqual(perimeter.geometry.coordinates[0][0]);
		expect(perimeter.geometry.coordinates[0][0]).toEqual([9, 52]);
		expect(dock.geometry).toMatchObject({ type: 'LineString' });
		expect(dock.geometry.coordinates).toHaveLength(2);
		expect(wire.geometry.coordinates).toEqual([]);
		expect(exclusion.idx).toBe(0);
	});
});

describe('files', () => {
	it('names the map after the file and the file after the map', () => {
		expect(baseName('C:\\maps\\Front yard.geojson')).toBe('Front yard');
		expect(baseName('.json')).toBe('Imported map');
		expect(exportFileName('Garten/hinten: Süd')).toBe('Garten_hinten_ Süd.geojson');
		expect(exportFileName('  ')).toBe('map.geojson');
	});

	it('offers a download', () => {
		const createObjectURL = vi.fn(() => 'blob:x');
		const revokeObjectURL = vi.fn();
		vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
		const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function (
			this: HTMLAnchorElement
		) {
			expect(this.download).toBe('a.geojson');
			expect(this.getAttribute('href')).toBe('blob:x');
		});
		downloadText('a.geojson', '{}');
		expect(click).toHaveBeenCalledOnce();
		expect(revokeObjectURL).toHaveBeenCalledWith('blob:x');
		expect(document.querySelector('a[download]')).toBeNull();
		vi.unstubAllGlobals();
		vi.restoreAllMocks();
	});
});
