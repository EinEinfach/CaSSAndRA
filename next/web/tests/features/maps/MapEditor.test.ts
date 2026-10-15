import { tick } from 'svelte';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MapEditor from '#features/maps/MapEditor.svelte';
import { emptyShape } from '#features/maps/editor.ts';
import type { MapShape } from '#features/maps/types.ts';
import { garden } from './fixtures.ts';

beforeEach(() => {
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			disconnect() {}
		}
	);
});
afterEach(() => vi.unstubAllGlobals());

// jsdom has no layout, so the canvas view stays 300x300 px. An empty map is
// shown at 20 px/m around (0,0); the garden (0..10 m) is fitted with 24 px
// padding: 252 px / 10 m around (5,5).
const emptyView = { cx: 0, cy: 0, scale: 20 };
const gardenView = { cx: 5, cy: 5, scale: 25.2 };

async function tap(x: number, y: number, view = gardenView) {
	const canvas = screen.getByLabelText('Map editor canvas');
	for (const type of ['pointerdown', 'pointerup']) {
		const ev = new MouseEvent(type, {
			clientX: 150 + (x - view.cx) * view.scale,
			clientY: 150 - (y - view.cy) * view.scale,
			bubbles: true
		});
		Object.defineProperty(ev, 'pointerId', { value: 1 });
		canvas.dispatchEvent(ev);
	}
	await tick();
}

const button = (name: string | RegExp) => screen.getByRole('button', { name }) as HTMLButtonElement;

describe('MapEditor', () => {
	it('draws a new map and saves it', async () => {
		const save = vi.fn<(m: MapShape) => Promise<void>>(async () => {});
		render(MapEditor, { initial: emptyShape(), save, cancel: vi.fn() });
		expect(button('Save map').disabled).toBe(true);
		expect(screen.getByText('Give the map a name.')).toBeTruthy();

		await userEvent.type(screen.getByLabelText('Map name'), 'Front');
		await tap(0, 0, emptyView);
		await tap(5, 0, emptyView);
		await tap(5, 5, emptyView);
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('3');
		expect(button('Save map').disabled).toBe(false);

		await userEvent.click(button('Save map'));
		expect(save.mock.calls[0][0]).toMatchObject({
			name: 'Front',
			perimeter: [
				{ x: 0, y: 0 },
				{ x: 5, y: 0 },
				{ x: 5, y: 5 }
			]
		});
	});

	it('edits the chosen part of the map', async () => {
		render(MapEditor, { initial: garden(), save: vi.fn(), cancel: vi.fn() });
		await userEvent.click(screen.getByRole('tab', { name: /Search wire/ }));
		await tap(6, 4);
		await tap(7, 4);
		expect(screen.getByRole('tab', { name: /Search wire/ }).textContent).toContain('2');

		await userEvent.click(button('+ Exclusion'));
		expect(screen.getByRole('tab', { name: /Exclusion 2/ }).getAttribute('aria-selected')).toBe(
			'true'
		);
		await userEvent.click(button('Remove exclusion'));
		expect(screen.queryByRole('tab', { name: /Exclusion 2/ })).toBeNull();
	});

	it('undoes, redoes and deletes with buttons and keys', async () => {
		render(MapEditor, { initial: garden(), save: vi.fn(), cancel: vi.fn() });
		expect(button('Undo').disabled).toBe(true);
		await tap(10, 10); // select a corner
		await userEvent.keyboard('{Delete}');
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('3');

		await userEvent.keyboard('{Control>}z{/Control}');
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('4');
		await userEvent.keyboard('{Control>}{Shift>}z{/Shift}{/Control}');
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('3');
		await userEvent.click(button('Undo'));
		await userEvent.click(button('Redo'));
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('3');
	});

	it('does not delete points while typing the name', async () => {
		render(MapEditor, { initial: garden(), save: vi.fn(), cancel: vi.fn() });
		await tap(10, 10);
		await userEvent.type(screen.getByLabelText('Map name'), '{Backspace}');
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('4');
	});

	it('adds the robot position as a point', async () => {
		render(MapEditor, {
			initial: emptyShape('x'),
			robotPosition: { x: 1.234, y: 2 },
			save: vi.fn(),
			cancel: vi.fn()
		});
		await userEvent.click(button(/Robot position/));
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('1');
	});

	it('cannot add the robot position without a robot', () => {
		render(MapEditor, { initial: emptyShape('x'), save: vi.fn(), cancel: vi.fn() });
		expect(button(/Robot position/).disabled).toBe(true);
	});

	it('shows save errors and cancels', async () => {
		const cancel = vi.fn();
		const save = vi.fn().mockRejectedValue(new Error('map name already taken'));
		render(MapEditor, { initial: garden(), save, cancel });
		await userEvent.click(button('Save map'));
		expect((await screen.findByRole('alert')).textContent).toBe('map name already taken');
		await userEvent.click(button('Cancel'));
		expect(cancel).toHaveBeenCalled();
	});
});
