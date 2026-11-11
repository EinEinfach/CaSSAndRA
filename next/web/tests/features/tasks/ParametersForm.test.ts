import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import ParametersForm from '#features/tasks/ParametersForm.svelte';
import type { Parameters } from '#features/tasks/types.ts';
import { parameters } from './fixtures.ts';

describe('ParametersForm', () => {
	it('edits the given parameters in place', async () => {
		const p: Parameters = parameters();
		render(ParametersForm, { parameters: p });
		await userEvent.click(screen.getByRole('radio', { name: 'Rings' }));
		const width = screen.getByLabelText(/Lane width/) as HTMLInputElement;
		await userEvent.clear(width);
		await userEvent.type(width, '0.2');
		await userEvent.click(screen.getByLabelText('Mow around exclusions'));
		expect(p).toMatchObject({ pattern: 'rings', widthM: 0.2, mowExclusions: false });
	});
});
