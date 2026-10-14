// Display texts for robot values.
import type { DockReason, RobotStatus } from './types.ts';

const statusLabels: Record<RobotStatus, string> = {
	offline: 'Offline',
	idle: 'Idle',
	move: 'Manual drive',
	'map upload': 'Uploading map',
	mow: 'Mowing',
	transit: 'Driving',
	docking: 'Docking',
	charging: 'Charging',
	docked: 'Docked',
	error: 'Error',
	unknown: 'Unknown'
};

export function statusLabel(status: RobotStatus): string {
	return statusLabels[status] ?? status;
}

/** Visual tone of a status: drives the badge color. */
export type Tone = 'neutral' | 'active' | 'good' | 'warning' | 'danger';

export function statusTone(status: RobotStatus): Tone {
	switch (status) {
		case 'mow':
		case 'transit':
		case 'move':
		case 'docking':
		case 'map upload':
			return 'active';
		case 'charging':
		case 'docked':
			return 'good';
		case 'error':
			return 'danger';
		case 'offline':
		case 'unknown':
			return 'warning';
		default:
			return 'neutral';
	}
}

const dockReasonLabels: Record<Exclude<DockReason, ''>, string> = {
	user: 'sent home by you',
	finished: 'route finished',
	'low battery': 'battery low',
	rain: 'rain',
	temperature: 'temperature'
};

export function dockReasonLabel(reason: DockReason): string {
	return reason === '' ? '' : dockReasonLabels[reason];
}

export function gpsLabel(solution: string, accuracyM: number, satellites: number): string {
	const name = solution === 'fix' ? 'Fix' : solution === 'float' ? 'Float' : 'No fix';
	if (solution !== 'fix' && solution !== 'float') return `${name} · ${satellites} sat`;
	return `${name} · ±${formatMeters(accuracyM)} · ${satellites} sat`;
}

export function formatMeters(m: number): string {
	return m < 1 ? `${Math.round(m * 100)} cm` : `${m.toFixed(1)} m`;
}

/** Commands that make sense in a status; the UI disables the others. */
export function canStart(status: RobotStatus): boolean {
	return ['idle', 'docked', 'charging', 'move'].includes(status);
}

export function canDock(status: RobotStatus): boolean {
	return !['offline', 'docking', 'docked', 'charging', 'map upload'].includes(status);
}

export function canStop(status: RobotStatus): boolean {
	return status !== 'offline';
}
