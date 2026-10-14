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

export type DockReason = '' | 'user' | 'finished' | 'low battery' | 'rain' | 'temperature';

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
	op: string;
	sensor: string;
	mowMotorOn: boolean;
	mowPointIndex: number;
	dockReason: DockReason;
	mapCrc: number;
	updatedAt: string | null;
}

export interface RobotMap {
	perimeter: Point[];
	exclusions: Point[][];
	dock: Point[];
	way: Point[];
}
