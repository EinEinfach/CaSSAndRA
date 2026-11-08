import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import RemoteControl from '#features/robot/RemoteControl.svelte';
import type { RobotStatus } from '#features/robot/types.ts';

function setup(status: RobotStatus = 'mow', mowMotorOn = false, speedMps = 0.25) {
	const actions = {
		setMowMotor: vi.fn(async () => {}),
		setSpeed: vi.fn(async () => {}),
		command: vi.fn(async () => {})
	};
	render(RemoteControl, { status, mowMotorOn, speedMps, actions });
	return actions;
}

const button = (name: string) => screen.getByRole('button', { name });

describe('RemoteControl', () => {
	it('starts the mow motor only after confirmation', async () => {
		const actions = setup('idle');
		const motor = screen.getByRole('switch', { name: 'Mow motor' }) as HTMLInputElement;

		await userEvent.click(motor);
		expect(motor.checked).toBe(false);
		expect(screen.getByRole('alertdialog').textContent).toContain('blade');
		await userEvent.click(button('Cancel'));
		expect(actions.setMowMotor).not.toHaveBeenCalled();

		await userEvent.click(motor);
		await userEvent.click(button('Start motor'));
		expect(actions.setMowMotor).toHaveBeenCalledWith(true);
	});

	it('stops the mow motor at once', async () => {
		const actions = setup('mow', true);
		await userEvent.click(screen.getByRole('switch', { name: 'Mow motor' }));
		expect(screen.queryByRole('alertdialog')).toBeNull();
		expect(actions.setMowMotor).toHaveBeenCalledWith(false);
	});

	it('changes the speed in steps of 1 cm/s while mowing', async () => {
		const actions = setup('mow', true, 0.25);
		expect(screen.getByText('Mow speed')).toBeTruthy();
		expect(screen.getByTestId('robot-speed').textContent).toBe('0.25 m/s');

		await userEvent.click(button('Faster'));
		await userEvent.click(button('Slower'));
		expect(actions.setSpeed).toHaveBeenNthCalledWith(1, 0.26);
		expect(actions.setSpeed).toHaveBeenNthCalledWith(2, 0.24);
	});

	it.each(['idle', 'docked', 'docking'] as const)('hides the speed when %s', (status) => {
		setup(status);
		expect(screen.queryByTestId('robot-speed')).toBeNull();
	});

	it('names the drive speed during goto', () => {
		setup('transit', false, 0.3);
		expect(screen.getByText('Drive speed')).toBeTruthy();
	});

	it.each([
		['Reboot', 'reboot', 'Reboot'],
		['Reboot GPS', 'reboot-gps', 'Reboot GPS'],
		['Shut down', 'shutdown', 'Shut down']
	])('asks before %s', async (label, name, confirmLabel) => {
		const actions = setup('idle');
		await userEvent.click(button(label));
		expect(actions.command).not.toHaveBeenCalled();
		const dialog = screen.getByRole('alertdialog');
		await userEvent.click(
			[...dialog.querySelectorAll('button')].find((b) => b.textContent === confirmLabel)!
		);
		expect(actions.command).toHaveBeenCalledWith(name);
		expect(screen.queryByRole('alertdialog')).toBeNull();
	});

	it('shows why a command failed', async () => {
		const actions = setup('mow', true);
		actions.setMowMotor.mockRejectedValueOnce(new Error('robot offline'));
		await userEvent.click(screen.getByRole('switch', { name: 'Mow motor' }));
		expect((await screen.findByRole('alert')).textContent).toBe('robot offline');
	});

	it.each(['offline', 'map upload'] as const)('sends nothing when %s', (status) => {
		setup(status);
		expect((screen.getByRole('switch', { name: 'Mow motor' }) as HTMLInputElement).disabled).toBe(
			true
		);
		expect((button('Reboot') as HTMLButtonElement).disabled).toBe(true);
	});
});
