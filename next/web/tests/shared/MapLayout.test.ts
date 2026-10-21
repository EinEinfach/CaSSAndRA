import { render, screen } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import LayoutHarness from './LayoutHarness.svelte';

describe('MapLayout', () => {
	it('puts the map first and the panel next to it', () => {
		render(LayoutHarness);
		const panel = screen.getByRole('complementary', { name: 'Things to do' });
		const map = screen.getByText('the map');
		expect(panel.textContent).toBe('the panel');
		expect(map.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
	});
});
