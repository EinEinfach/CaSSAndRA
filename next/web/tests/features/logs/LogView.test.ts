import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { LogFeed } from '#features/logs/feed.svelte.ts';
import LogView from '#features/logs/LogView.svelte';
import { entry, manualScheduler } from './fixtures.ts';

async function setup() {
	const feed = new LogFeed(
		vi.fn(async () => [
			entry(1, 'link online feature=link', 'DEBUG'),
			entry(2, 'command cmd=mow'),
			entry(3, 'robot error sensor=bumper', 'ERROR')
		]),
		manualScheduler()
	);
	await feed.poll();
	render(LogView, { feed });
	return feed;
}

const lines = () => within(screen.getByRole('log', { name: 'Log lines' }));

describe('LogView', () => {
	it('shows the lines with time and level', async () => {
		await setup();
		expect(lines().getByText('command cmd=mow')).toBeTruthy();
		expect(lines().getByText('ERROR')).toBeTruthy();
		expect(lines().getAllByRole('time')).toHaveLength(3);
	});

	it('filters by text and level', async () => {
		await setup();
		const user = userEvent.setup();
		await user.type(screen.getByLabelText('Filter log'), 'bumper');
		expect(lines().queryByText('command cmd=mow')).toBeNull();
		expect(lines().getByText('robot error sensor=bumper')).toBeTruthy();
		await user.clear(screen.getByLabelText('Filter log'));
		await user.selectOptions(screen.getByLabelText('Lowest level'), 'INFO');
		expect(lines().queryByText(/link online/)).toBeNull();
		await user.type(screen.getByLabelText('Filter log'), 'nothing');
		expect(lines().getByText('No line matches.')).toBeTruthy();
	});

	it('pauses, resumes and clears', async () => {
		const feed = await setup();
		const user = userEvent.setup();
		await user.click(screen.getByRole('button', { name: 'Pause' }));
		expect(feed.paused).toBe(true);
		expect(screen.getByRole('button', { name: 'Resume' }).getAttribute('aria-pressed')).toBe(
			'true'
		);
		await user.click(screen.getByRole('button', { name: 'Resume' }));
		expect(feed.paused).toBe(false);
		await user.click(screen.getByRole('button', { name: 'Clear' }));
		expect(lines().getByText('No log lines yet.')).toBeTruthy();
	});

	it('says when the log cannot be loaded', async () => {
		const feed = new LogFeed(
			vi.fn(async () => Promise.reject(new Error('offline'))),
			manualScheduler()
		);
		await feed.poll();
		render(LogView, { feed });
		expect(screen.getByRole('alert').textContent).toContain('Cannot load the log: offline');
	});
});
