// Smooth robot movement on the map: between two reported poses the robot
// glides from where it is drawn to the new pose, taking as long as the reports
// are apart (like CaSSAndRA_native). Works in meters, so zoom and pan do not
// disturb it.
import type { RobotPose } from '#shared/drawMap.ts';
import type { RobotStatus } from './types.ts';

/** Statuses in which the robot drives by itself or by joystick. */
export function animatesMotion(status: RobotStatus): boolean {
	return ['mow', 'transit', 'docking', 'move'].includes(status);
}

/** target expressed as the angle closest to from, so the robot turns the short way. */
export function nearestAngle(from: number, target: number): number {
	const d = target - from;
	return from + d - 2 * Math.PI * Math.round(d / (2 * Math.PI));
}

/** The pose a fraction f (0..1) of the way from a to b; b's heading must be near a's. */
export function interpolatePose(a: RobotPose, b: RobotPose, f: number): RobotPose {
	return {
		position: {
			x: a.position.x + (b.position.x - a.position.x) * f,
			y: a.position.y + (b.position.y - a.position.y) * f
		},
		headingRad: a.headingRad + (b.headingRad - a.headingRad) * f
	};
}

/** Time and animation frames; the browser's by default, fakes in tests. */
export interface FrameClock {
	now(): number;
	request(fn: () => void): unknown;
	cancel(handle: unknown): void;
}

export const browserFrames: FrameClock = {
	now: () => performance.now(),
	request: (fn) => requestAnimationFrame(fn),
	cancel: (h) => cancelAnimationFrame(h as number)
};

export class RobotMotion {
	/** The pose to draw; follows update() and moves on every frame while animating. */
	pose = $state.raw<RobotPose | null>(null);

	private from: RobotPose | null = null;
	private to: RobotPose | null = null;
	private start = 0;
	private duration = 0;
	private lastUpdate = -Infinity;
	private frame: unknown = null;

	/** maxMs bounds a glide, so a robot reporting after a long gap does not crawl. */
	constructor(
		private clock: FrameClock = browserFrames,
		private maxMs = 2000
	) {}

	/** A new reported pose; animate = glide there, otherwise jump. Null hides the robot. */
	update(target: RobotPose | null, animate: boolean): void {
		const now = this.clock.now();
		const since = now - this.lastUpdate;
		this.lastUpdate = now;
		this.stopFrames();
		const current = this.at(now);
		if (!target || !current || !animate || since <= 0 || since > this.maxMs) {
			this.from = this.to = null;
			this.pose = target;
			return;
		}
		this.from = current;
		this.to = { ...target, headingRad: nearestAngle(current.headingRad, target.headingRad) };
		this.start = now;
		this.duration = since;
		this.tick();
	}

	/** Stops animating (e.g. when the map goes away). */
	stop(): void {
		this.stopFrames();
		if (this.to) this.pose = this.to;
		this.from = this.to = null;
	}

	private at(now: number): RobotPose | null {
		if (!this.from || !this.to) return this.pose;
		return interpolatePose(this.from, this.to, Math.min(1, (now - this.start) / this.duration));
	}

	private tick = () => {
		const now = this.clock.now();
		this.pose = this.at(now);
		this.frame = now - this.start < this.duration ? this.clock.request(this.tick) : null;
	};

	private stopFrames() {
		if (this.frame !== null) this.clock.cancel(this.frame);
		this.frame = null;
	}
}
