import { render, screen, within } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import ScheduleEditor from '#features/schedule/ScheduleEditor.svelte';
import type { Schedule, ScheduleView } from '#features/schedule/types.ts';
import { task } from '../tasks/fixtures.ts';
import { view } from './fixtures.ts';

const tasks = [
	task('t1', 'Front'),
	task('t2', 'Back'),
	task('t3', 'Edges'),
	task('y1', 'Yard all', { mapId: 'm2' })
];
const maps = [
	{ id: 'm1', name: 'Garden' },
	{ id: 'm2', name: 'Yard' }
];

function setup(v: ScheduleView | null = view()) {
	const save = vi.fn(async (s: Schedule): Promise<ScheduleView> => ({ ...view(), schedule: s }));
	const r = render(ScheduleEditor, {
		view: v,
		tasks,
		maps,
		activeMapId: 'm1',
		save,
		now: new Date(2026, 9, 26, 8, 0)
	});
	return { save, ...r };
}

const monday = () => screen.getAllByRole('listitem')[0];

describe('ScheduleEditor', () => {
	it('waits for the schedule', () => {
		setup(null);
		expect(screen.getByText('Loading the schedule…')).toBeTruthy();
	});

	it('shows the week with windows, tasks in order and the status', () => {
		setup(
			view({
				status: { state: 'waiting', message: '', next: new Date(2026, 9, 26, 9).toISOString() }
			})
		);
		expect(screen.getByTestId('schedule-status').textContent).toBe('Next start: today 09:00.');
		expect(screen.getAllByRole('listitem')).toHaveLength(7);
		expect((screen.getByLabelText('Monday from') as HTMLSelectElement).value).toBe('09:00');
		expect((screen.getByLabelText('Monday until') as HTMLSelectElement).value).toBe('12:00');
		const chips = [...monday().querySelectorAll('.chip .name')].map((e) => e.textContent);
		expect(chips).toEqual(['Front', 'Back']);
		expect(screen.queryByLabelText('Tuesday from')).toBeNull();
		expect((screen.getByLabelText('Mow on Tuesday') as HTMLInputElement).checked).toBe(false);
	});

	it('edits a day and saves the whole week', async () => {
		const { save } = setup();
		await userEvent.click(screen.getByLabelText('Mow on Tuesday'));
		await userEvent.selectOptions(screen.getByLabelText('Tuesday from'), '07:30');
		await userEvent.selectOptions(screen.getByLabelText('Add a task on Tuesday'), 't3');
		await userEvent.click(screen.getByLabelText('Remove Back from Monday'));
		expect(screen.getByText('Unsaved changes')).toBeTruthy();

		await userEvent.click(screen.getByRole('button', { name: 'Save' }));
		const sent = save.mock.calls[0][0];
		expect(sent.days[0].taskIds).toEqual(['t1']);
		expect(sent.days[1]).toEqual({ start: '07:30', end: '15:00', taskIds: ['t3'] });
		expect(await screen.findByText('Saved')).toBeTruthy();
	});

	it('offers only tasks of the day’s map that are not chosen yet', () => {
		setup();
		const add = within(monday()).getByLabelText('Add a task on Monday');
		expect(
			within(add)
				.getAllByRole('option')
				.map((o) => o.textContent)
		).toEqual(['+ Task', 'Edges']);
	});

	it('warns when the tasks belong to another map than the active one', () => {
		const v = view();
		v.schedule.days[0].taskIds = ['y1'];
		setup(v);
		expect(
			screen.getByText(/belong to Yard; they only start while it is the active map/)
		).toBeTruthy();
	});

	it('explains a day without tasks', async () => {
		setup();
		await userEvent.click(screen.getByLabelText('Mow on Sunday'));
		expect(screen.getByText('No tasks: the robot continues the route it has.')).toBeTruthy();
	});

	it('discards changes and shows why saving failed', async () => {
		const { save } = setup();
		await userEvent.click(screen.getByRole('checkbox', { name: /^Mow by schedule/ }));
		await userEvent.click(screen.getByRole('button', { name: 'Discard' }));
		expect(screen.queryByText('Unsaved changes')).toBeNull();
		expect(
			(screen.getByRole('checkbox', { name: /^Mow by schedule/ }) as HTMLInputElement).checked
		).toBe(true);

		save.mockRejectedValueOnce(new Error('invalid schedule'));
		await userEvent.click(screen.getByRole('checkbox', { name: /^Mow by schedule/ }));
		await userEvent.click(screen.getByRole('button', { name: 'Save' }));
		expect((await screen.findByRole('alert')).textContent).toBe('invalid schedule');
	});

	it('follows changes from elsewhere unless something is edited', async () => {
		const { rerender } = setup();
		const changed = view();
		changed.schedule.days[0].end = '13:00';
		await rerender({ view: changed });
		expect((screen.getByLabelText('Monday until') as HTMLSelectElement).value).toBe('13:00');

		await userEvent.click(screen.getByLabelText('Mow on Friday'));
		const again = view();
		again.schedule.days[0].end = '14:00';
		await rerender({ view: again });
		expect((screen.getByLabelText('Monday until') as HTMLSelectElement).value).toBe('13:00');
		expect(screen.getByText('Unsaved changes')).toBeTruthy();
	});
});
