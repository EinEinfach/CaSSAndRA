// Maps as sent by the backend (maps/map.go, maps/api.go).
import type { Point } from '#shared/viewport.ts';

export interface GardenMap {
	id: string;
	name: string;
	perimeter: Point[];
	exclusions: Point[][];
	/** Path into the docking station; the last point is the station. */
	dock: Point[];
	searchWire: Point[];
	updatedAt: string;
}

export interface MapList {
	activeId: string;
	maps: GardenMap[];
}

/** The editable part of a map. */
export type MapShape = Pick<GardenMap, 'name' | 'perimeter' | 'exclusions' | 'dock' | 'searchWire'>;
