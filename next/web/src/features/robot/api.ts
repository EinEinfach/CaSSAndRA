// Robot commands and queries (robot/api.go).
import { getJSON, post } from '#shared/api.ts';
import type { RobotMap, RobotState } from './types.ts';

export type SimpleCommand =
	'stop' | 'dock' | 'mow' | 'goto' | 'skip-next-point' | 'reboot' | 'reboot-gps' | 'shutdown';

export const command = (name: SimpleCommand, fetchFn: typeof fetch = fetch) =>
	post(`/api/robot/${name}`, undefined, fetchFn);

export const move = (linear: number, angular: number, fetchFn: typeof fetch = fetch) =>
	post('/api/robot/move', { linear, angular }, fetchFn);

export const setMowMotor = (on: boolean, fetchFn: typeof fetch = fetch) =>
	post('/api/robot/mow-motor', { on }, fetchFn);

export const fetchState = (fetchFn: typeof fetch = fetch) =>
	getJSON<RobotState>('/api/robot/state', fetchFn);

export const fetchMap = (fetchFn: typeof fetch = fetch) =>
	getJSON<RobotMap>('/api/robot/map', fetchFn);
