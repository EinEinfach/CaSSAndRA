import { describe, expect, it } from 'vitest';
import {
	canDock,
	canStart,
	canStop,
	dockReasonLabel,
	batteryLabel,
	formatAmps,
	formatMeters,
	formatPoint,
	gpsLabel,
	satellitesLabel,
	statusLabel,
	statusTone
} from '#features/robot/format.ts';
import type { RobotStatus } from '#features/robot/types.ts';

const all: RobotStatus[] = [
	'offline',
	'idle',
	'move',
	'map upload',
	'mow',
	'transit',
	'docking',
	'charging',
	'docked',
	'error',
	'unknown'
];

describe('status texts', () => {
	it('has a label and tone for every status', () => {
		for (const s of all) {
			expect(statusLabel(s), s).not.toBe(s); // a real label, not the raw value
		}
		expect(statusLabel('mow')).toBe('Mowing');
		expect(statusTone('mow')).toBe('active');
		expect(statusTone('charging')).toBe('good');
		expect(statusTone('error')).toBe('danger');
		expect(statusTone('offline')).toBe('warning');
		expect(statusTone('idle')).toBe('neutral');
	});

	it('shows unknown statuses from a newer backend as they are', () => {
		expect(statusLabel('lawn party' as RobotStatus)).toBe('lawn party');
	});

	it('explains dock reasons', () => {
		expect(dockReasonLabel('')).toBe('');
		expect(dockReasonLabel('rain')).toBe('rain');
		expect(dockReasonLabel('user')).toBe('sent home by you');
		expect(dockReasonLabel('schedule')).toBe('schedule ended');
		expect(dockReasonLabel('finished')).toBe('route finished');
	});
});

describe('gpsLabel and formatMeters', () => {
	it('shows accuracy only with a solution', () => {
		expect(gpsLabel('fix', 0.02, 28)).toBe('Fix · ±2 cm · 28 sat');
		expect(gpsLabel('float', 1.5, 12)).toBe('Float · ±1.5 m · 12 sat');
		expect(gpsLabel('invalid', 0, 3)).toBe('No fix · 3 sat');
	});

	it('formats short distances in cm', () => {
		expect(formatMeters(0.004)).toBe('0 cm');
		expect(formatMeters(0.999)).toBe('100 cm');
		expect(formatMeters(12.34)).toBe('12.3 m');
	});
});

describe('allowed commands', () => {
	it.each([
		['idle', true, true, true],
		['docked', true, true, false],
		['charging', true, true, false],
		['mow', false, true, true],
		['transit', false, true, true],
		['docking', false, true, false],
		['error', false, true, true],
		['map upload', false, true, false],
		['offline', false, false, false]
	] as [RobotStatus, boolean, boolean, boolean][])(
		'%s: start %s, stop %s, dock %s',
		(status, start, stop, dock) => {
			expect(canStart(status)).toBe(start);
			expect(canStop(status)).toBe(stop);
			expect(canDock(status)).toBe(dock);
		}
	);
});

describe('satellites, battery and points', () => {
	it('formats like the legacy status cards', () => {
		expect(satellitesLabel(12, 20, 0.64)).toBe('12/20 · 0.6 s');
		expect(batteryLabel(85, 27.14)).toBe('85 % · 27.1 V');
		expect(formatAmps(-1.25)).toBe('-1.3 A');
		expect(formatPoint({ x: -1, y: 2.345 })).toBe('-1.00, 2.35 m');
	});
});
