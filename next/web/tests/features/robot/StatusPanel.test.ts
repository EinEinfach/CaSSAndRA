import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import StatusPanel from '#features/robot/StatusPanel.svelte';
import { robotState } from './fixtures.ts';

describe('StatusPanel', () => {
	it('shows status, battery and GPS', () => {
		render(StatusPanel, {
			state: robotState({ status: 'mow', amps: -1.25 }),
			connected: true
		});

		expect(screen.getByTestId('robot-status').textContent).toBe('Mowing');
		expect(screen.getByTestId('robot-battery').textContent).toBe('90 % · 27.4 V');
		expect(screen.getByText('-1.3 A')).toBeTruthy();
		expect(screen.getByText('Fix · ±2 cm · 28 sat')).toBeTruthy();
		expect(screen.getByText('20/28 · 0.6 s')).toBeTruthy();
	});

	it('has the details like the legacy info box', () => {
		render(StatusPanel, {
			state: robotState({ mowPointIndex: 42, target: { x: 3, y: -4.5 } }),
			connected: true
		});

		expect(screen.getByText('Details')).toBeTruthy();
		expect(screen.getByText('1.00, 2.00 m')).toBeTruthy();
		expect(screen.getByText('3.00, -4.50 m')).toBeTruthy();
		expect(screen.getByText('42')).toBeTruthy();
		expect(screen.getByText('3 cm')).toBeTruthy();
		expect(screen.getByText('Sunray 1.0.332')).toBeTruthy();
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
