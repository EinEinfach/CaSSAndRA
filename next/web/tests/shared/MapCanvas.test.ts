import { render, screen } from '@testing-library/svelte';
import { tick } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import MapCanvas from '#shared/MapCanvas.svelte';
import { RobotPictureSource } from '#shared/robotPicture.svelte.ts';
import PictureMapHarness from './PictureMapHarness.svelte';
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

// jsdom has no layout: getBoundingClientRect is all zeros, so client = canvas pixels.
function pointer(el: Element, type: string, x: number, y: number, pointerId = 1) {
	const ev = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true });
	Object.defineProperty(ev, 'pointerId', { value: pointerId });
	el.dispatchEvent(ev);
}

describe('MapCanvas', () => {
	it('renders a labelled canvas and draws the layers', () => {
		render(MapCanvas, { layers: { perimeter }, label: 'Garden' });

		expect(screen.getByLabelText('Garden').tagName).toBe('CANVAS');
		expect(ctx.shapes.some((s) => s.op === 'fill' && s.closed)).toBe(true);
	});

	it('draws the robot picture of the layout once it has loaded', async () => {
		const image = {} as CanvasImageSource;
		const source = new RobotPictureSource(() => Promise.resolve(image));
		const robot = { position: { x: 5, y: 5 }, headingRad: 0 };
		render(PictureMapHarness, { source, layers: { perimeter, robot } });
		expect(ctx.images).toEqual([]);
		expect(ctx.shapes.some((s) => s.color === '#888' && s.points.length === 4)).toBe(true); // arrow

		await source.set('alfred', 100);
		await tick();

		expect(ctx.images.at(-1)?.image).toBe(image);
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

	it('reports taps in world coordinates and pans otherwise', async () => {
		const tap = vi.fn();
		render(MapCanvas, { layers: {}, interact: { tap } });
		const canvas = screen.getByLabelText('Map');
		// Empty map: 20 px per meter, world (0,0) in the middle of 300x300.
		pointer(canvas, 'pointerdown', 170, 130);
		pointer(canvas, 'pointerup', 170, 130);
		expect(tap).toHaveBeenCalledWith({ x: 1, y: 1 }, 1 / 20);

		pointer(canvas, 'pointerdown', 150, 150);
		pointer(canvas, 'pointermove', 190, 150);
		pointer(canvas, 'pointerup', 190, 150);
		expect(tap).toHaveBeenCalledTimes(1); // a drag is no tap
		expect(await screen.findByRole('button', { name: 'Fit' })).toBeTruthy();
	});

	it('drags instead of panning when press grabs something', () => {
		const press = vi.fn(() => true);
		const move = vi.fn();
		const release = vi.fn();
		const tap = vi.fn();
		render(MapCanvas, { layers: {}, interact: { press, move, release, tap } });
		const canvas = screen.getByLabelText('Map');

		pointer(canvas, 'pointerdown', 150, 150);
		pointer(canvas, 'pointermove', 170, 150);
		pointer(canvas, 'pointerup', 170, 150);

		expect(press).toHaveBeenCalledWith({ x: 0, y: 0 }, 1 / 20);
		expect(move).toHaveBeenCalledWith({ x: 1, y: 0 });
		expect(release).toHaveBeenCalledOnce();
		expect(tap).not.toHaveBeenCalled();
		expect(screen.queryByRole('button', { name: 'Fit' })).toBeNull();
	});

	it('does not tap with two fingers or on cancel', () => {
		const tap = vi.fn();
		render(MapCanvas, { layers: {}, interact: { tap } });
		const canvas = screen.getByLabelText('Map');
		pointer(canvas, 'pointerdown', 150, 150, 1);
		pointer(canvas, 'pointerdown', 160, 150, 2);
		pointer(canvas, 'pointerup', 160, 150, 2);
		pointer(canvas, 'pointerup', 150, 150, 1);
		pointer(canvas, 'pointerdown', 150, 150, 3);
		pointer(canvas, 'pointercancel', 150, 150, 3);
		expect(tap).not.toHaveBeenCalled();
	});

	it.each([
		['once', true],
		['always', false]
	] as const)('in fit mode %s keeps the view on new data: %s', async (fitMode, keeps) => {
		const lawn = () => ctx.shapes.filter((s) => s.op === 'fill' && s.closed).at(-1)!.points[1];
		const { rerender } = render(MapCanvas, { layers: { perimeter }, fitMode });
		const before = lawn();
		await rerender({
			layers: {
				perimeter,
				dock: [
					{ x: 100, y: 100 },
					{ x: 101, y: 100 }
				]
			},
			fitMode
		});
		expect(lawn()[0] === before[0] && lawn()[1] === before[1]).toBe(keeps);
	});

	it('survives a browser without 2D canvas', () => {
		vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
		expect(() => render(MapCanvas, { layers: { perimeter } })).not.toThrow();
	});
});
