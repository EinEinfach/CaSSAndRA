import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import AreaTools from '#features/tasks/AreaTools.svelte';
import { PlanSession } from '#features/tasks/session.svelte.ts';
import { parameters } from './fixtures.ts';

function setup() {
	const session = new PlanSession();
	session.useDefaults(parameters());
	render(AreaTools, { session });
	return session;
}

describe('AreaTools', () => {
	it('switches the tool and explains it', async () => {
		const session = setup();
		expect(screen.getByText(/whole garden\./)).toBeTruthy();
		await userEvent.click(screen.getByRole('radio', { name: 'Rectangle' }));
		expect(session.tool).toBe('rectangle');
		expect(screen.getByText(/Drag on the map/)).toBeTruthy();
	});

	it('clears the selection', async () => {
		const session = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Polygon' }));
		session.tap({ x: 1, y: 1 });
		session.tap({ x: 2, y: 1 });
		await userEvent.click(screen.getByRole('button', { name: 'Remove last corner' }));
		expect(session.selection).toEqual([{ x: 1, y: 1 }]);
		await userEvent.click(screen.getByRole('button', { name: 'Clear selection' }));
		expect(session.selection).toEqual([]);
	});
});
