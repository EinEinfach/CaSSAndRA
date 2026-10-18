import { describe, expect, it } from 'vitest';
import {
	animatesMotion,
	interpolatePose,
	nearestAngle,
	RobotMotion
} from '#features/robot/motion.svelte.ts';
import { fakeFrames } from './fixtures.ts';

const pose = (x: number, y: number, headingRad = 0) => ({ position: { x, y }, headingRad });

describe('animatesMotion', () => {
	it.each([
		['mow', true],
		['transit', true],
		['docking', true],
		['move', true],
		['idle', false],
		['charging', false],
		['offline', false]
	] as const)('%s -> %s', (status, want) => {
		expect(animatesMotion(status)).toBe(want);
	});
});

describe('nearestAngle', () => {
	it.each([
		[0, 1, 1],
		[3, -3, 2 * Math.PI - 3], // across ±π: turn 0.28 rad, not 6
		[-3, 3, 3 - 2 * Math.PI],
		[10 * Math.PI, 0.5, 10 * Math.PI + 0.5]
	])('from %f to %f -> %f', (from, target, want) => {
		expect(nearestAngle(from, target)).toBeCloseTo(want, 9);
	});
});

describe('interpolatePose', () => {
	it('moves position and heading linearly', () => {
		expect(interpolatePose(pose(0, 0, 0), pose(4, -2, 1), 0.25)).toEqual(pose(1, -0.5, 0.25));
	});
});

describe('RobotMotion', () => {
	it('jumps to the first pose', () => {
		const f = fakeFrames();
		const m = new RobotMotion(f.clock);
		m.update(pose(1, 1), true);
		expect(m.pose).toEqual(pose(1, 1));
		expect(f.pending()).toBe(0);
	});

	it('glides to the next pose in the time since the last report', () => {
		const f = fakeFrames();
		const m = new RobotMotion(f.clock);
		m.update(pose(0, 0), true);
		f.advance(1000);
		m.update(pose(2, 0, 1), true);
		expect(m.pose).toEqual(pose(0, 0, 0));

		f.advance(250);
		expect(m.pose).toEqual(pose(0.5, 0, 0.25));
		f.advance(750);
		expect(m.pose).toEqual(pose(2, 0, 1));
		expect(f.pending()).toBe(0);
	});

	it('starts the next glide where the robot is drawn', () => {
		const f = fakeFrames();
		const m = new RobotMotion(f.clock);
		m.update(pose(0, 0), true);
		f.advance(1000);
		m.update(pose(2, 0), true);
		f.advance(500); // halfway, at x = 1
		m.update(pose(1, 2), true);

		f.advance(250); // half of the 500 ms since the last report
		expect(m.pose?.position).toEqual({ x: 1, y: 1 });
	});

	it('turns the short way across ±π', () => {
		const f = fakeFrames();
		const m = new RobotMotion(f.clock);
		m.update(pose(0, 0, 3), true);
		f.advance(1000);
		m.update(pose(0, 0, -3), true);
		f.advance(500);
		expect(m.pose!.headingRad).toBeCloseTo(Math.PI, 9);
	});

	it('jumps when not animating, after a long gap and when hidden', () => {
		const f = fakeFrames();
		const m = new RobotMotion(f.clock, 2000);
		m.update(pose(0, 0), true);
		f.advance(1000);
		m.update(pose(1, 0), false);
		expect(m.pose).toEqual(pose(1, 0));

		f.advance(5000);
		m.update(pose(9, 9), true);
		expect(m.pose).toEqual(pose(9, 9));

		m.update(null, true);
		expect(m.pose).toBeNull();
		expect(f.pending()).toBe(0);
	});

	it('stop ends a glide at its target', () => {
		const f = fakeFrames();
		const m = new RobotMotion(f.clock);
		m.update(pose(0, 0), true);
		f.advance(1000);
		m.update(pose(2, 0), true);
		m.stop();
		expect(m.pose).toEqual(pose(2, 0));
		expect(f.pending()).toBe(0);
	});
});
