import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MapCanvas from '#shared/MapCanvas.svelte';
import { recordingContext } from './recordingContext.ts';

let ctx: ReturnType<typeof recordingContext>;

beforeEach(() => {
	ctx = recordingContext();
	Object.assign(ctx, { setTransform: vi.fn() });
	vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockImplementation(
		() => ctx as unknown as CanvasRenderingContext2D
	);
	vi.stubGlobal(
		'ResizeObserver',
		class {
			observe() {}
			disconnect() {}
		}
	);
});

afterEach(() => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
});

const perimeter = [
	{ x: 0, y: 0 },
	{ x: 10, y: 0 },
	{ x: 10, y: 10 }
];

describe('MapCanvas', () => {
	it('renders a labelled canvas and draws the layers', () => {
		render(MapCanvas, { layers: { perimeter }, label: 'Garden' });

		expect(screen.getByLabelText('Garden').tagName).toBe('CANVAS');
		expect(ctx.shapes.some((s) => s.op === 'fill' && s.closed)).toBe(true);
	});

	it('redraws when the layers change', async () => {
		const { rerender } = render(MapCanvas, { layers: { perimeter } });
		const before = ctx.rects.length;

		await rerender({ layers: { perimeter, target: { x: 5, y: 5 } } });

		expect(ctx.rects.length).toBeGreaterThan(before);
	});

	it('shows a fit button after the user zooms and hides it after fitting', async () => {
		render(MapCanvas, { layers: { perimeter } });
		expect(screen.queryByRole('button', { name: 'Fit' })).toBeNull();

		screen
			.getByLabelText('Map')
			.dispatchEvent(new WheelEvent('wheel', { deltaY: -100, cancelable: true }));
		const button = await screen.findByRole('button', { name: 'Fit' });

		button.click();
		await vi.waitFor(() => expect(screen.queryByRole('button', { name: 'Fit' })).toBeNull());
	});

	it('survives a browser without 2D canvas', () => {
		vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
		expect(() => render(MapCanvas, { layers: { perimeter } })).not.toThrow();
	});
});
