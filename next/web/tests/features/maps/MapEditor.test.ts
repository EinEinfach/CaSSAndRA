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
			robotSolution: 'fix',
			save: vi.fn(),
			cancel: vi.fn()
		});
		await userEvent.click(button(/Robot position/));
		expect(screen.getByRole('tab', { name: /Perimeter/ }).textContent).toContain('1');
	});

	it.each(['float', 'invalid', null])(
		'asks before adding a position with solution %s',
		async (s) => {
			render(MapEditor, {
				initial: emptyShape('x'),
				robotPosition: { x: 1, y: 2 },
				robotSolution: s,
				save: vi.fn(),
				cancel: vi.fn()
			});
			const points = () => screen.getByRole('tab', { name: /Perimeter/ }).textContent;
			await userEvent.click(button(/Robot position/));
			expect(screen.getByRole('alertdialog').textContent).toContain('no RTK fix');
			expect(points()).toContain('0');
			await userEvent.click(button("Don't add"));
			expect(screen.queryByRole('alertdialog')).toBeNull();
			expect(points()).toContain('0');

			await userEvent.click(button(/Robot position/));
			await userEvent.click(button('Add anyway'));
			expect(screen.queryByRole('alertdialog')).toBeNull();
			expect(points()).toContain('1');
		}
	);

	it('draws an area and adds it to the lawn', async () => {
		const lawn = {
			perimeter: [
				{ x: 0, y: 0 },
				{ x: 14, y: 0 },
				{ x: 14, y: 10 },
				{ x: 0, y: 10 }
			],
			exclusions: []
		};
		const reshape = vi.fn(async () => lawn);
		const save = vi.fn(async () => {});
		render(MapEditor, { initial: garden(), reshape, save, cancel: vi.fn() });

		await userEvent.click(screen.getByRole('tab', { name: /Area/ }));
		expect(button('Add to lawn').disabled).toBe(true);
		await tap(5, 5);
		await tap(8, 5);
		await tap(8, 8);
		await userEvent.click(button('Add to lawn'));

		const g = garden();
		expect(reshape).toHaveBeenCalledWith(
			{ perimeter: g.perimeter, exclusions: g.exclusions },
			[
				{ x: 5, y: 5 },
				{ x: 8, y: 5 },
				{ x: 8, y: 8 }
			],
			'add'
		);
		// The area is used up and the perimeter is edited again.
		expect(screen.getByRole('tab', { name: /Area/ }).textContent).toContain('0');
		expect(screen.getByRole('tab', { name: /Perimeter/ }).getAttribute('aria-selected')).toBe(
			'true'
		);
		await userEvent.click(button('Save map'));
		// Saved without the area.
		expect(save).toHaveBeenCalledWith({
			name: g.name,
			dock: g.dock,
			searchWire: g.searchWire,
			...lawn
		});

		await userEvent.click(button('Undo'));
		expect(screen.getByRole('tab', { name: /Area/ }).textContent).toContain('3');
	});

	it('cuts an area out and shows why it failed', async () => {
		const reshape = vi.fn().mockRejectedValue(new Error('the lawn would fall into 2 pieces'));
		render(MapEditor, { initial: garden(), reshape, save: vi.fn(), cancel: vi.fn() });
		await userEvent.click(screen.getByRole('tab', { name: /Area/ }));
		await tap(5, 5);
		await tap(8, 5);
		await tap(8, 8);
		await userEvent.click(button('Cut out of lawn'));
		expect(reshape.mock.calls[0][2]).toBe('subtract');
		expect((await screen.findByRole('alert')).textContent).toBe(
			'the lawn would fall into 2 pieces'
		);
		expect(screen.getByRole('tab', { name: /Area/ }).textContent).toContain('3');
	});

	it('adds robot positions in the order of the drive, taps on the nearest edge', async () => {
		const save = vi.fn(async () => {});
		render(MapEditor, {
			initial: garden(),
			robotPosition: { x: 5, y: 0.1 }, // next to the first edge
			robotSolution: 'fix',
			save,
			cancel: vi.fn()
		});
		await userEvent.click(button(/Robot position/));
		await tap(10, 5); // on the second edge
		await userEvent.click(button('Save map'));
		expect(save).toHaveBeenCalledWith(
			expect.objectContaining({
				perimeter: [
					{ x: 0, y: 0 },
					{ x: 10, y: 0 },
					{ x: 10, y: 5 },
					{ x: 10, y: 10 },
					{ x: 0, y: 10 },
					{ x: 5, y: 0.1 }
				]
			})
		);
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
