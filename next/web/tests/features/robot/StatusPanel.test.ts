import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import StatusPanel from '#features/robot/StatusPanel.svelte';
import { robotState } from './fixtures.ts';

describe('StatusPanel', () => {
	it('shows status, battery and GPS', () => {
		render(StatusPanel, {
			state: robotState({ status: 'mow', mowMotorOn: true }),
			connected: true
		});

		expect(screen.getByTestId('robot-status').textContent).toBe('Mowing');
		expect(screen.getByTestId('robot-battery').textContent).toBe('90 % · 27.4 V');
		expect(screen.getByText('Fix · ±2 cm · 28 sat')).toBeTruthy();
		expect(screen.getByText('on')).toBeTruthy();
	});

	it('shows the dock reason and sensor problems', () => {
		render(StatusPanel, {
			state: robotState({ status: 'docking', dockReason: 'rain', sensor: 'rain' }),
			connected: true
		});

		expect(screen.getByText('Docking')).toBeTruthy();
		expect(screen.getAllByText('rain')).toHaveLength(2);
	});

	it('shows offline while the connection to CaSSAndRA is lost', () => {
		render(StatusPanel, { state: robotState({ status: 'mow' }), connected: false });

		expect(screen.getByTestId('robot-status').textContent).toBe('Offline');
		expect(screen.getByRole('status').textContent).toContain('reconnecting');
		expect(screen.queryByTestId('robot-battery')).toBeNull();
	});

	it('shows offline before the first state', () => {
		render(StatusPanel, { state: null, connected: true });
		expect(screen.getByTestId('robot-status').textContent).toBe('Offline');
	});
});
