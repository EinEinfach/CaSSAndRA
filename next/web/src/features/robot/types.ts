// Robot data as sent by the backend (robot/api.go).
import type { Point } from '#shared/viewport.ts';

export type RobotStatus =
	| 'offline'
	| 'idle'
	| 'move'
	| 'map upload'
	| 'mow'
	| 'transit'
	| 'docking'
	| 'charging'
	| 'docked'
	| 'error'
	| 'unknown';

export type DockReason =
	'' | 'user' | 'schedule' | 'finished' | 'low battery' | 'rain' | 'temperature';

export interface RobotState {
	status: RobotStatus;
	online: boolean;
	firmware: string;
	firmwareVersion: string;
	position: Point;
	headingRad: number;
	target: Point;
	batteryV: number;
	socPercent: number;
	amps: number;
	solution: string;
	accuracyM: number;
	satellites: number;
	/** Satellites with correction data. */
	satellitesDgps: number;
	/** Age of the correction data. */
	dgpsAgeSec: number;
	/** Distance from the line to the target. */
	lateralErrorM: number;
	op: string;
	sensor: string;
	mowMotorOn: boolean;
	/** Speed of mowing or goto as last commanded (the robot does not report it); 0 otherwise. */
	speedMps: number;
	mowPointIndex: number;
	/** A mow route on the robot was left before its end; "mow" continues it. */
	resumable: boolean;
	dockReason: DockReason;
	mapCrc: number;
	updatedAt: string | null;
	/** Changes when the trail starts anew (docked or cleared): fetch it again. */
	trailId: number;
	/** Obstacles the robot found on its way, as polygons. */
	obstacles: Point[][];
}

export interface RobotMap {
	perimeter: Point[];
	exclusions: Point[][];
	dock: Point[];
	way: Point[];
}

/** The path driven since the robot last docked (GET /api/robot/trail). */
export interface Trail {
	id: number;
	points: Point[];
}
