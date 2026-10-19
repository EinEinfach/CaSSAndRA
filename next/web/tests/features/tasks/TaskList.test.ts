import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import TaskList from '#features/tasks/TaskList.svelte';
import { parameters, task } from './fixtures.ts';

function setup(chosen: string[] = [], busy = false) {
	const toggle = vi.fn();
	const edit = vi.fn();
	const remove = vi.fn();
	const two = task('b', 'Back', {
		parts: [
			{ selection: [], parameters: parameters() },
			{ selection: [], parameters: parameters() }
		]
	});
	render(TaskList, { tasks: [task('a', 'Front'), two], chosen, busy, toggle, edit, remove });
	return { toggle, edit, remove, two };
}

describe('TaskList', () => {
	it('shows the tasks, their parts and the chosen order', () => {
		setup(['b', 'a']);
		const items = screen.getAllByRole('listitem');
		expect(items[0].textContent).toContain('Front');
		expect(items[0].textContent).toContain('2'); // mowed second
		expect(items[1].textContent).toContain('2 parts');
		expect((screen.getByLabelText('Mow Back') as HTMLInputElement).checked).toBe(true);
	});

	it('chooses and edits tasks', async () => {
		const { toggle, edit, two } = setup();
		await userEvent.click(screen.getByLabelText('Mow Front'));
		expect(toggle).toHaveBeenCalledWith('a');
		await userEvent.click(screen.getAllByRole('button', { name: 'Edit' })[1]);
		expect(edit).toHaveBeenCalledWith(two);
	});

	it('deletes only after a second press', async () => {
		const { remove } = setup();
		await userEvent.click(screen.getByRole('button', { name: 'Delete Front' }));
		expect(remove).not.toHaveBeenCalled();
		await userEvent.click(screen.getByRole('button', { name: 'Keep' }));
		await userEvent.click(screen.getByRole('button', { name: 'Delete Front' }));
		await userEvent.click(screen.getByRole('button', { name: 'Delete Front?' }));
		expect(remove).toHaveBeenCalledWith('a');
	});

	it('says when there are no tasks', () => {
		render(TaskList, {
			tasks: [],
			chosen: [],
			busy: false,
			toggle: vi.fn(),
			edit: vi.fn(),
			remove: vi.fn()
		});
		expect(screen.getByText(/No saved tasks/)).toBeTruthy();
	});
});
