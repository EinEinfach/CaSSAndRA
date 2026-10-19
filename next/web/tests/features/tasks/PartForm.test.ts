import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import PartForm from '#features/tasks/PartForm.svelte';
import { PlanSession } from '#features/tasks/session.svelte.ts';
import { parameters } from './fixtures.ts';

function setup() {
	const session = new PlanSession();
	session.useDefaults(parameters());
	render(PartForm, { session });
	return session;
}

describe('PartForm', () => {
	it('is empty until the defaults are known', () => {
		render(PartForm, { session: new PlanSession() });
		expect(screen.queryByRole('tablist')).toBeNull();
	});

	it('binds the parameters of the current part', async () => {
		const session = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Squares' }));
		const laps = screen.getByLabelText(/Border laps/) as HTMLInputElement;
		await userEvent.clear(laps);
		await userEvent.type(laps, '3');
		await userEvent.click(screen.getByLabelText('Border counter-clockwise'));
		expect(session.part!.parameters).toMatchObject({
			pattern: 'squares',
			borderLaps: 3,
			borderCcw: true
		});
	});

	it('adds, switches and removes parts', async () => {
		const session = setup();
		await userEvent.click(screen.getByRole('button', { name: '+ Part' }));
		expect(session.parts).toHaveLength(2);
		expect(screen.getByText(/one after another/)).toBeTruthy();
		await userEvent.click(screen.getByRole('radio', { name: 'Polygon' }));
		await userEvent.click(screen.getByRole('tab', { name: 'Part 1' }));
		expect((screen.getByRole('radio', { name: 'Whole garden' }) as HTMLInputElement).checked).toBe(
			true
		);
		await userEvent.click(screen.getByRole('button', { name: 'Remove part 1' }));
		expect(session.parts).toHaveLength(1);
		expect(session.tool).toBe('polygon');
	});

	it('offers to undo corners only for polygons', async () => {
		const session = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Rectangle' }));
		expect(screen.queryByRole('button', { name: 'Remove last corner' })).toBeNull();
		await userEvent.click(screen.getByRole('radio', { name: 'Polygon' }));
		const undo = screen.getByRole('button', { name: 'Remove last corner' }) as HTMLButtonElement;
		expect(undo.disabled).toBe(true);
		session.tap({ x: 1, y: 1 });
		await userEvent.click(screen.getByRole('button', { name: 'Remove last corner' }));
		expect(session.selection).toEqual([]);
	});
});
