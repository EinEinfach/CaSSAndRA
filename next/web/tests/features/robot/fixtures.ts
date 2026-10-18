// Shared test data for the robot feature.
import type { FrameClock } from '#features/robot/motion.svelte.ts';
import type { RobotState } from '#features/robot/types.ts';

export function robotState(overrides: Partial<RobotState> = {}): RobotState {
	return {
		status: 'idle',
		online: true,
		firmware: 'Sunray',
		firmwareVersion: '1.0.332',
		position: { x: 1, y: 2 },
		headingRad: 0,
		target: { x: 3, y: 4 },
		batteryV: 27.4,
		socPercent: 90,
		amps: 0.1,
		solution: 'fix',
		accuracyM: 0.02,
		satellites: 28,
		op: 'idle',
		sensor: 'none',
		mowMotorOn: false,
		mowPointIndex: 0,
		dockReason: '',
		mapCrc: 1234,
		updatedAt: '2026-06-01T12:00:00Z',
		...overrides
	};
}

/** Time moves only when the test says so; frames run on flush(). */
export function fakeFrames() {
	let time = 0;
	let next = 1;
	const pending = new Map<number, () => void>();
	const clock: FrameClock = {
		now: () => time,
		request: (fn) => {
			pending.set(next, fn);
			return next++;
		},
		cancel: (h) => pending.delete(h as number)
	};
	return {
		clock,
		pending: () => pending.size,
		/** Advances time by ms and runs the frames that were waiting. */
		advance(ms: number) {
			time += ms;
			const fns = [...pending.values()];
			pending.clear();
			fns.forEach((fn) => fn());
		}
	};
}
