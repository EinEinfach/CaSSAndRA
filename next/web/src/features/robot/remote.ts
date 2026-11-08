// Remote control beyond mow/stop/dock: mow motor, speed and the robot's system commands.
import type { RobotStatus } from './types.ts';

/** Legacy CaSSAndRA steps the speed by 1 cm/s per click. */
export const SPEED_STEP_MPS = 0.01;
export const MIN_SPEED_MPS = 0.01;
export const MAX_SPEED_MPS = 1;

/** The speed can be changed while the robot follows a route. */
export function canChangeSpeed(status: RobotStatus): boolean {
	return status === 'mow' || status === 'transit';
}

export function speedLabel(status: RobotStatus): string {
	return status === 'transit' ? 'Drive speed' : 'Mow speed';
}

/** The speed one step up (+1) or down (-1), kept within the firmware's range. */
export function nextSpeed(currentMps: number, direction: 1 | -1): number {
	const next = Math.round((currentMps + direction * SPEED_STEP_MPS) * 100) / 100;
	return Math.min(MAX_SPEED_MPS, Math.max(MIN_SPEED_MPS, next));
}

export function formatSpeed(mps: number): string {
	return `${mps.toFixed(2)} m/s`;
}

/** The robot has to be reachable; during a map upload it would interfere. */
export function canSendRemote(status: RobotStatus): boolean {
	return status !== 'offline' && status !== 'map upload';
}

export type SystemCommand = 'reboot' | 'reboot-gps' | 'shutdown';

/** An action that waits for the user to confirm it. */
export interface Confirmation {
	question: string;
	confirmLabel: string;
	/** Drawn as dangerous (red). */
	danger: boolean;
}

export const systemCommands: { name: SystemCommand; label: string; confirm: Confirmation }[] = [
	{
		name: 'reboot',
		label: 'Reboot',
		confirm: {
			question: 'Restart the Sunray firmware? The robot stops and is offline for a while.',
			confirmLabel: 'Reboot',
			danger: false
		}
	},
	{
		name: 'reboot-gps',
		label: 'Reboot GPS',
		confirm: {
			question: 'Restart the GPS receiver? The robot has no fix until it is back.',
			confirmLabel: 'Reboot GPS',
			danger: false
		}
	},
	{
		name: 'shutdown',
		label: 'Shut down',
		confirm: {
			question: 'Switch the robot off? It can only be switched on again at the robot.',
			confirmLabel: 'Shut down',
			danger: true
		}
	}
];

/** Starting the blade needs a confirmation, stopping it never waits. */
export const mowMotorOnConfirmation: Confirmation = {
	question: 'Start the mow motor? Keep clear of the blade.',
	confirmLabel: 'Start motor',
	danger: true
};
