import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import ThemePicker from '#features/settings/ThemePicker.svelte';
import { Theme } from '#shared/theme.svelte.ts';

describe('ThemePicker', () => {
	it('switches the theme of this device at once', async () => {
		const root = document.createElement('html');
		const theme = new Theme({ storage: null, media: null, root });
		render(ThemePicker, { theme });
		expect((screen.getByRole('radio', { name: 'System' }) as HTMLInputElement).checked).toBe(true);
		await userEvent.click(screen.getByRole('radio', { name: 'Dark' }));
		expect(theme.choice).toBe('dark');
		expect(root.dataset.theme).toBe('dark');
		expect((screen.getByRole('radio', { name: 'Dark' }) as HTMLInputElement).checked).toBe(true);
	});
});
