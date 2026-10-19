import { fireEvent, render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import Progress from '#features/robot/Progress.svelte';

function setup(
	props: Partial<{ status: 'mow' | 'idle'; mowPointIndex: number; routeLength: number }> = {}
) {
	const skipNext = vi.fn(async () => {});
	const skipTo = vi.fn<(fraction: number) => Promise<void>>(async () => {});
	const result = render(Progress, {
		status: 'mow',
		mowPointIndex: 42,
		routeLength: 100,
		skipNext,
		skipTo,
		...props
	});
	return { skipNext, skipTo, ...result };
}

const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('Progress', () => {
	it('shows how far the robot is along the route', () => {
		setup();
		expect(screen.getByTestId('route-progress').textContent).toBe('42 %');
		expect(screen.getByRole('progressbar').getAttribute('aria-valuenow')).toBe('42');
	});

	it('is hidden while the robot does not follow a route', () => {
		setup({ status: 'idle' });
		expect(screen.queryByLabelText('Route progress')).toBeNull();
		setup({ routeLength: 0 });
		expect(screen.queryByLabelText('Route progress')).toBeNull();
	});

	it('jumps to the chosen progress only on request', async () => {
		const { skipTo } = setup();
		expect(button('Jump').disabled).toBe(true);
		await fireEvent.input(screen.getByLabelText('Jump to progress'), { target: { value: '70' } });
		expect(skipTo).not.toHaveBeenCalled();
		expect(screen.getByText('Jump to 70 %')).toBeTruthy();
		await userEvent.click(button('Jump'));
		expect(skipTo).toHaveBeenCalledWith(0.7);
		expect(button('Jump').disabled).toBe(true); // back to following the robot
	});

	it('skips the next point', async () => {
		const { skipNext } = setup();
		await userEvent.click(button('Skip point'));
		expect(skipNext).toHaveBeenCalledOnce();
	});

	it('shows a failed command', async () => {
		const { skipNext } = setup();
		skipNext.mockRejectedValueOnce(new Error('robot is offline'));
		await userEvent.click(button('Skip point'));
		expect(screen.getByRole('alert').textContent).toBe('robot is offline');
	});
});
