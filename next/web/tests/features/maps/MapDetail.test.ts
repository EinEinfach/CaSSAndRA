import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MapDetail from '#features/maps/MapDetail.svelte';
import { garden } from './fixtures.ts';

beforeEach(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			disconnect() {}
		}
	);
});
afterEach(() => vi.unstubAllGlobals());

function setup(active = false) {
	const actions = {
		upload: vi.fn(async () => {}),
		activate: vi.fn(async () => {}),
		remove: vi.fn(async () => {})
	};
	const props = {
		map: garden(),
		active,
		onedit: vi.fn(),
		onduplicate: vi.fn(),
		ondeleted: vi.fn(),
		actions
	};
	const r = render(MapDetail, props);
	return { ...props, ...r };
}

const button = (name: string) => screen.getByRole('button', { name });

describe('MapDetail', () => {
	it('summarizes the map (the page draws it)', () => {
		setup(true);
		expect(screen.getByRole('heading').textContent).toBe('Garden');
		expect(screen.getByText(/4 perimeter points · 1 exclusions · dock path 2 points/)).toBeTruthy();
		expect(screen.getByText('On robot')).toBeTruthy();
		expect(document.querySelector('canvas')).toBeNull();
		expect(screen.queryByRole('button', { name: 'Show on live view' })).toBeNull();
	});

	it('sends the map to the robot', async () => {
		const { actions } = setup();
		await userEvent.click(button('Send to robot'));
		expect(actions.upload).toHaveBeenCalledWith('m1');
		expect((await screen.findByRole('status')).textContent).toBe('Sent to the robot.');
	});

	it('shows why sending failed', async () => {
		const { actions } = setup();
		actions.upload.mockRejectedValueOnce(new Error('robot is driving, stop it first'));
		await userEvent.click(button('Send to robot'));
		expect((await screen.findByRole('alert')).textContent).toBe('robot is driving, stop it first');
	});

	it('activates, edits and duplicates', async () => {
		const { actions, onedit, onduplicate } = setup();
		await userEvent.click(button('Show on live view'));
		expect(actions.activate).toHaveBeenCalledWith('m1');
		await userEvent.click(button('Edit'));
		await userEvent.click(button('Duplicate'));
		expect(onedit).toHaveBeenCalled();
		expect(onduplicate).toHaveBeenCalled();
	});

	it('deletes only after confirmation', async () => {
		const { actions, ondeleted } = setup();
		await userEvent.click(button('Delete'));
		await userEvent.click(button('Keep'));
		expect(actions.remove).not.toHaveBeenCalled();

		await userEvent.click(button('Delete'));
		await userEvent.click(button('Really delete'));
		expect(actions.remove).toHaveBeenCalledWith('m1');
		expect(ondeleted).toHaveBeenCalled();
	});

	it('keeps the message when the same map updates, clears it for another map', async () => {
		const { rerender } = setup();
		await userEvent.click(button('Send to robot'));
		await screen.findByRole('status');
		await rerender({ map: { ...garden(), updatedAt: 'later' } });
		expect(screen.queryByRole('status')).not.toBeNull();
		await rerender({ map: garden('m2', 'Yard') });
		expect(screen.queryByRole('status')).toBeNull();
	});
});
