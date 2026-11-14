import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import MapList from '#features/maps/MapList.svelte';
import { garden } from './fixtures.ts';

describe('MapList', () => {
	it('lists the maps, marks the active and selected one', async () => {
		const onselect = vi.fn();
		render(MapList, {
			maps: [garden('m1', 'Garden'), { ...garden('m2', 'Yard'), exclusions: [], dock: [] }],
			activeId: 'm2',
			selectedId: 'm1',
			onselect,
			oncreate: vi.fn()
		});
		const items = screen.getAllByRole('button').filter((b) => b.classList.contains('item'));
		expect(items.map((b) => b.textContent?.replace(/\s+/g, ' ').trim())).toEqual([
			'Garden 1 exclusion · dock',
			'Yard 0 exclusions On robot'
		]);
		expect(items[0].getAttribute('aria-current')).toBe('true');

		await userEvent.click(items[1]);
		expect(onselect).toHaveBeenCalledWith('m2');
	});

	it('invites to create the first map', async () => {
		const oncreate = vi.fn();
		render(MapList, { maps: [], activeId: '', selectedId: null, onselect: vi.fn(), oncreate });
		expect(screen.getByText(/No maps yet/)).toBeTruthy();
		await userEvent.click(screen.getByRole('button', { name: '+ New map' }));
		expect(oncreate).toHaveBeenCalled();
	});

	it('passes a chosen file on and offers Import only when it can', async () => {
		const onimport = vi.fn();
		const props = {
			maps: [],
			activeId: '',
			selectedId: null,
			onselect: vi.fn(),
			oncreate: vi.fn()
		};
		const { unmount } = render(MapList, props);
		expect(screen.queryByRole('button', { name: 'Import' })).toBeNull();
		unmount();

		render(MapList, { ...props, onimport });
		expect(screen.getByRole('button', { name: 'Import' })).toBeTruthy();
		const file = new File(['[]'], 'maps.json', { type: 'application/json' });
		const input = screen.getByLabelText('Map file to import') as HTMLInputElement;
		await userEvent.upload(input, file);
		expect(onimport).toHaveBeenCalledWith(file);
		expect(input.value).toBe('');
	});
});
