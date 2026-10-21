import { render, screen } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';
import { tick } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RobotMap from '#features/robot/RobotMap.svelte';
import { recordingContext } from '../../shared/recordingContext.ts';
import { fakeFrames, robotState } from './fixtures.ts';

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
	// Give the map recognisable colors so shapes can be told apart.
	document.documentElement.style.setProperty('--map-robot', 'robot-color');
	document.documentElement.style.setProperty('--map-target', 'target-color');
	document.documentElement.style.setProperty('--map-way-done', 'done-color');
	document.documentElement.style.setProperty('--map-trail', 'trail-color');
	document.documentElement.style.setProperty('--map-selection', 'goal-color');
});

afterEach(() => {
	vi.restoreAllMocks();
	vi.unstubAllGlobals();
});

const map = {
	perimeter: [
		{ x: 0, y: 0 },
		{ x: 10, y: 0 },
		{ x: 10, y: 10 }
	],
	exclusions: [],
	dock: [],
	way: [
		{ x: 1, y: 1 },
		{ x: 9, y: 1 },
		{ x: 9, y: 9 }
	]
};
const colorsDrawn = () => ctx.shapes.map((s) => s.color);

describe('RobotMap', () => {
	it('draws robot, target and progress while mowing', () => {
		render(RobotMap, { state: robotState({ status: 'mow', mowPointIndex: 1 }), map, trail: [] });

		expect(screen.getByLabelText('Garden map with robot position')).toBeTruthy();
		expect(colorsDrawn()).toEqual(
			expect.arrayContaining(['robot-color', 'target-color', 'done-color'])
		);
	});

	it('hides robot and target while offline', () => {
		render(RobotMap, { state: robotState({ status: 'offline' }), map, trail: [] });
		expect(colorsDrawn()).not.toContain('robot-color');
		expect(colorsDrawn()).not.toContain('target-color');
	});

	it('hides the target while idle', () => {
		render(RobotMap, { state: robotState({ status: 'idle' }), map, trail: [] });
		expect(colorsDrawn()).toContain('robot-color');
		expect(colorsDrawn()).not.toContain('target-color');
	});

	it('glides the robot to a new position, with the trail ending at it', async () => {
		const frames = fakeFrames();
		const at = (x: number) => robotState({ status: 'mow', position: { x, y: 5 } });
		const trailEnd = () =>
			ctx.shapes
				.filter((s) => s.color === 'trail-color')
				.at(-1)!
				.points.at(-1)!;
		const props = (x: number) => ({
			state: at(x),
			map,
			trail: [
				{ x: 0, y: 5 },
				{ x, y: 5 }
			],
			frames: frames.clock
		});
		const { rerender } = render(RobotMap, props(2));
		const start = trailEnd();

		frames.advance(1000);
		await rerender(props(6));
		frames.advance(500);
		await tick();
		const half = trailEnd();
		frames.advance(500);
		await tick();
		const end = trailEnd();

		expect(end[0]).toBeGreaterThan(start[0]);
		expect(half[0]).toBeCloseTo((start[0] + end[0]) / 2, 6);
		expect(half[1]).toBeCloseTo(start[1], 6);
	});

	it('offers to clear the trail once there is one', async () => {
		const clearTrail = vi.fn(async () => {});
		const props = (trail: { x: number; y: number }[]) => ({
			state: robotState({ status: 'mow' }),
			map,
			trail,
			clearTrail
		});
		const { rerender } = render(RobotMap, props([{ x: 1, y: 2 }]));
		expect(screen.queryByRole('button', { name: 'Clear trail' })).toBeNull();

		await rerender(
			props([
				{ x: 0, y: 2 },
				{ x: 1, y: 2 }
			])
		);
		await userEvent.click(screen.getByRole('button', { name: 'Clear trail' }));
		expect(clearTrail).toHaveBeenCalledOnce();
	});

	it('shows a picked goal and passes taps on the map', async () => {
		const tap = vi.fn();
		render(RobotMap, {
			state: robotState({ status: 'idle' }),
			map,
			trail: [],
			interact: { tap },
			goal: { x: 4, y: 4 }
		});
		await tick();
		expect(colorsDrawn()).toContain('goal-color');
		const canvas = screen.getByLabelText('Garden map with robot position');
		for (const type of ['pointerdown', 'pointerup']) {
			const ev = new MouseEvent(type, { clientX: 150, clientY: 150, bubbles: true });
			Object.defineProperty(ev, 'pointerId', { value: 1 });
			canvas.dispatchEvent(ev);
		}
		expect(tap).toHaveBeenCalledOnce();
	});
});
