import { render, screen } from '@testing-library/svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import RobotMap from '#features/robot/RobotMap.svelte';
import { recordingContext } from '../../shared/recordingContext.ts';
import { robotState } from './fixtures.ts';

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
});
