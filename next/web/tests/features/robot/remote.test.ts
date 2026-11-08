import { describe, expect, it } from 'vitest';
import {
	canChangeSpeed,
	canSendRemote,
	formatSpeed,
	nextSpeed,
	speedLabel,
	systemCommands
} from '#features/robot/remote.ts';

describe('remote control', () => {
	it('steps the speed by 1 cm/s within 0.01..1 m/s', () => {
		expect(nextSpeed(0.25, 1)).toBe(0.26);
		expect(nextSpeed(0.25, -1)).toBe(0.24);
		expect(nextSpeed(0.29, 1)).toBe(0.3); // no 0.30000000000000004
		expect(nextSpeed(1, 1)).toBe(1);
		expect(nextSpeed(0.01, -1)).toBe(0.01);
	});

	it('changes the speed only while following a route', () => {
		expect(canChangeSpeed('mow')).toBe(true);
		expect(canChangeSpeed('transit')).toBe(true);
		expect(canChangeSpeed('docking')).toBe(false);
		expect(canChangeSpeed('idle')).toBe(false);
		expect(speedLabel('transit')).toBe('Drive speed');
		expect(speedLabel('mow')).toBe('Mow speed');
		expect(formatSpeed(0.3)).toBe('0.30 m/s');
	});

	it('needs a reachable robot', () => {
		expect(canSendRemote('offline')).toBe(false);
		expect(canSendRemote('map upload')).toBe(false);
		expect(canSendRemote('error')).toBe(true);
	});

	it('marks only the shutdown as dangerous', () => {
		expect(systemCommands.filter((c) => c.confirm.danger).map((c) => c.name)).toEqual(['shutdown']);
	});
});
