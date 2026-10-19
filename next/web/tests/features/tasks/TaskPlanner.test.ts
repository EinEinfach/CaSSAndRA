import { tick } from 'svelte';
import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import TaskPlanner from '#features/tasks/TaskPlanner.svelte';
import type { PreviewRequest } from '#features/tasks/types.ts';
import { garden, pts } from '../maps/fixtures.ts';
import { parameters, plan } from './fixtures.ts';

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

// jsdom has no layout: the 300x300 px canvas shows the garden (0..10 m) at
// 25.2 px/m around (5,5), see MapEditor.test.ts.
const view = { cx: 5, cy: 5, scale: 25.2 };

function pointer(type: string, x: number, y: number) {
	const canvas = screen.getByLabelText('Map for planning a route');
	const ev = new MouseEvent(type, {
		clientX: 150 + (x - view.cx) * view.scale,
		clientY: 150 - (y - view.cy) * view.scale,
		bubbles: true
	});
	Object.defineProperty(ev, 'pointerId', { value: 1 });
	canvas.dispatchEvent(ev);
}

const button = (name: string | RegExp) => screen.getByRole('button', { name }) as HTMLButtonElement;

function setup(props: Partial<Parameters<typeof render<typeof TaskPlanner>>[1]> = {}) {
	const preview = vi.fn(async (req: PreviewRequest) => plan({ selection: req.selection }));
	const discard = vi.fn(async () => {});
	const start = vi.fn(async () => {});
	const result = render(TaskPlanner, {
		map: garden(),
		plan: null,
		planLoaded: true,
		defaults: parameters(),
		mowSpeedMps: 0.25,
		robotStatus: 'idle',
		preview,
		discard,
		start,
		...props
	});
	return { preview, discard, start, ...result };
}

describe('TaskPlanner', () => {
	it('plans the whole garden with the default parameters', async () => {
		const { preview } = setup();
		await userEvent.click(button('Calculate route'));
		expect(preview).toHaveBeenCalledWith({ selection: [], parameters: parameters() });
	});

	it('sends changed parameters', async () => {
		const { preview } = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Rings' }));
		const angle = screen.getByLabelText(/Angle/) as HTMLInputElement;
		await userEvent.clear(angle);
		await userEvent.type(angle, '45');
		await userEvent.click(screen.getByLabelText('Mow around exclusions'));
		await userEvent.click(button('Calculate route'));
		expect(preview).toHaveBeenCalledWith({
			selection: [],
			parameters: parameters({ pattern: 'rings', angleDeg: 45, mowExclusions: false })
		});
	});

	it('plans a rectangle dragged on the map', async () => {
		const { preview } = setup();
		await userEvent.click(screen.getByRole('radio', { name: 'Rectangle' }));
		expect(button('Calculate route').disabled).toBe(true);
		expect(screen.getByText('Select a part of the garden first.')).toBeTruthy();

		pointer('pointerdown', 1, 1);
		pointer('pointermove', 3, 2);
		pointer('pointermove', 5, 4);
		pointer('pointerup', 5, 4);
		await tick();
		await userEvent.click(button('Calculate route'));
		const sel = preview.mock.calls[0][0].selection;
		expect(sel).toHaveLength(4);
		expect(sel[0].x).toBeCloseTo(1, 1);
		expect(sel[2].y).toBeCloseTo(4, 1);
	});

	it('shows the planned route and notices changes since', async () => {
		const { rerender } = setup({ plan: plan() });
		const result = screen.getByLabelText('Planned route');
		expect(result.textContent).toContain('1.4 km');
		expect(result.textContent).toContain('4 points');
		expect(result.textContent).toContain('about 1 h 30 min');
		expect(screen.queryByText(/changed since/)).toBeNull();

		await userEvent.click(screen.getByRole('radio', { name: 'Squares' }));
		expect(screen.getByText(/changed since/)).toBeTruthy();

		await rerender({ plan: plan({ mapId: 'other' }) });
		expect(screen.queryByLabelText('Planned route')).toBeNull();
	});

	it('opens with the area and parameters of the current plan', async () => {
		const sel = pts(1, 1, 4, 1, 4, 4);
		const { preview } = setup({
			plan: plan({ selection: sel, parameters: parameters({ widthM: 0.3 }) })
		});
		expect((screen.getByRole('radio', { name: 'Polygon' }) as HTMLInputElement).checked).toBe(true);
		expect((screen.getByLabelText(/Lane width/) as HTMLInputElement).value).toBe('0.3');
		await userEvent.click(button('Calculate route'));
		expect(preview).toHaveBeenCalledWith({
			selection: sel,
			parameters: parameters({ widthM: 0.3 })
		});
	});

	it('starts mowing the planned route', async () => {
		const { start } = setup({ plan: plan() });
		await userEvent.click(button('Start mowing'));
		expect(start).toHaveBeenCalledOnce();
	});

	it('does not start a route that no longer matches the form', async () => {
		const { start } = setup({ plan: plan() });
		await userEvent.click(screen.getByRole('radio', { name: 'Squares' }));
		expect(button('Start mowing').disabled).toBe(true);
		await userEvent.click(button('Start mowing'));
		expect(start).not.toHaveBeenCalled();
	});

	it('waits for the robot to stand still before starting', async () => {
		const { rerender } = setup({ plan: plan(), robotStatus: 'mow' });
		expect(button('Start mowing').disabled).toBe(true);
		expect(screen.getByText(/idle or in the dock/)).toBeTruthy();
		await rerender({ robotStatus: 'charging' });
		expect(button('Start mowing').disabled).toBe(false);
	});

	it('shows why the robot did not start', async () => {
		setup({
			plan: plan(),
			start: vi.fn(async () => Promise.reject(new Error('robot is offline')))
		});
		await userEvent.click(button('Start mowing'));
		expect(screen.getByRole('alert').textContent).toBe('robot is offline');
	});

	it('discards the route', async () => {
		const { discard } = setup({ plan: plan() });
		await userEvent.click(button('Discard route'));
		expect(discard).toHaveBeenCalled();
	});

	it('shows why a route could not be computed', async () => {
		setup({ preview: vi.fn(async () => Promise.reject(new Error('no active map'))) });
		await userEvent.click(button('Calculate route'));
		expect(screen.getByRole('alert').textContent).toBe('no active map');
		expect(button('Calculate route').disabled).toBe(false);
	});

	it('asks for a map when none is active', () => {
		setup({ map: null });
		expect(screen.getByText(/No active map/)).toBeTruthy();
		expect(screen.queryByRole('button', { name: 'Calculate route' })).toBeNull();
	});
});
