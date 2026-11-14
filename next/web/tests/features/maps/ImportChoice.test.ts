import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import ImportChoice from '#features/maps/ImportChoice.svelte';
import { emptyShape } from '#features/maps/editor.ts';
import { pts } from './fixtures.ts';

describe('ImportChoice', () => {
	it('lists the maps of the file and opens the picked one', async () => {
		const front = {
			...emptyShape('maps 1'),
			perimeter: pts(0, 0, 1, 0, 1, 1),
			exclusions: [pts(0, 0, 1, 0, 1, 1)],
			dock: pts(0, 0, 1, 1)
		};
		const back = { ...emptyShape('maps 4'), perimeter: pts(0, 0, 4, 0, 4, 4, 0, 4) };
		const onpick = vi.fn();
		const ondismiss = vi.fn();
		render(ImportChoice, { fileName: 'maps.json', maps: [front, back], onpick, ondismiss });

		expect(screen.getByRole('heading').textContent).toBe('2 maps in maps.json');
		expect(screen.getByRole('button', { name: /maps 1/ }).textContent).toContain(
			'3 points · 1 exclusion · dock'
		);
		await userEvent.click(screen.getByRole('button', { name: /maps 4/ }));
		expect(onpick).toHaveBeenCalledWith(back);
		await userEvent.click(screen.getByRole('button', { name: 'Close' }));
		expect(ondismiss).toHaveBeenCalledOnce();
	});
});
