// Manual driving: from joystick offset to drive commands, and sending them.

export interface Drive {
	linear: number; // m/s, forward positive
	angular: number; // rad/s, counter-clockwise positive
}

export interface JoystickLimits {
	maxLinear: number;
	maxAngular: number;
	/** Fraction of the radius around the center that does nothing. */
	deadzone: number;
}

export const defaultLimits: JoystickLimits = { maxLinear: 0.5, maxAngular: 1, deadzone: 0.15 };

const round = (v: number) => Math.round(v * 100) / 100 || 0; // also turns -0 into 0

/**
 * dx/dy: offset of the knob from the center in pixels (screen y down).
 * Up drives forward, left turns left.
 */
export function driveFromOffset(
	dx: number,
	dy: number,
	radius: number,
	limits = defaultLimits
): Drive {
	let x = dx / radius;
	let y = -dy / radius;
	const len = Math.hypot(x, y);
	if (len > 1) {
		x /= len;
		y /= len;
	}
	if (Math.hypot(x, y) < limits.deadzone) return { linear: 0, angular: 0 };
	return { linear: round(y * limits.maxLinear), angular: round(-x * limits.maxAngular) };
}

export interface Scheduler {
	setInterval(fn: () => void, ms: number): unknown;
	clearInterval(handle: unknown): void;
}

const browserScheduler: Scheduler = {
	setInterval: (fn, ms) => setInterval(fn, ms),
	clearInterval: (h) => clearInterval(h as ReturnType<typeof setInterval>)
};

/**
 * Sends the current drive command repeatedly while the joystick is held and a
 * final stop when it is released. Repeating recovers from a lost request and
 * keeps the backend status at "move".
 */
export class MoveSender {
	private current: Drive = { linear: 0, angular: 0 };
	private handle: unknown = null;

	constructor(
		private send: (d: Drive) => Promise<void>,
		private intervalMs = 200,
		private scheduler: Scheduler = browserScheduler,
		private onError: (err: unknown) => void = (err) => console.error('move failed', err)
	) {}

	update(d: Drive): void {
		const changed = d.linear !== this.current.linear || d.angular !== this.current.angular;
		this.current = d;
		if (this.handle === null) {
			this.handle = this.scheduler.setInterval(() => this.emit(), this.intervalMs);
			this.emit();
		} else if (changed) {
			this.emit();
		}
	}

	release(): void {
		if (this.handle === null) return;
		this.scheduler.clearInterval(this.handle);
		this.handle = null;
		this.current = { linear: 0, angular: 0 };
		this.emit();
	}

	get active(): boolean {
		return this.handle !== null;
	}

	private emit() {
		this.send(this.current).catch(this.onError);
	}
}
