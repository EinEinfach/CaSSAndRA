import { describe, expect, it, vi } from 'vitest';
import { MoveSender, driveFromOffset, type Drive, type Scheduler } from '#features/robot/drive.ts';

describe('driveFromOffset', () => {
	const limits = { maxLinear: 0.5, maxAngular: 1, deadzone: 0.15 };

	it.each([
		['center', 0, 0, 0, 0],
		['inside the deadzone', 5, -5, 0, 0],
		['full up', 0, -100, 0.5, 0],
		['full down', 0, 100, -0.5, 0],
		['full left turns left', -100, 0, 0, 1],
		['full right turns right', 100, 0, 0, -1],
		['beyond the edge is clamped', 0, -300, 0.5, 0],
		['half up', 0, -50, 0.25, 0]
	])('%s', (_, dx, dy, linear, angular) => {
		expect(driveFromOffset(dx, dy, 100, limits)).toEqual({ linear, angular });
	});

	it('keeps diagonal speeds inside the circle', () => {
		const d = driveFromOffset(-100, -100, 100, limits);
		expect(d.linear).toBeCloseTo(0.35, 2);
		expect(d.angular).toBeCloseTo(0.71, 2);
	});
});

/** A scheduler driven by the test instead of real time. */
function fakeScheduler() {
	let fn: (() => void) | null = null;
	const s: Scheduler & { tick(): void; running(): boolean } = {
		setInterval: (f) => {
			fn = f;
			return 1;
		},
		clearInterval: () => {
			fn = null;
		},
		tick: () => fn?.(),
		running: () => fn !== null
	};
	return s;
}

describe('MoveSender', () => {
	function setup() {
		const sent: Drive[] = [];
		const scheduler = fakeScheduler();
		const sender = new MoveSender(async (d) => void sent.push(d), 200, scheduler);
		return { sent, scheduler, sender };
	}

	it('sends at once, repeats while held and stops on release', () => {
		const { sent, scheduler, sender } = setup();
		sender.update({ linear: 0.2, angular: 0 });
		expect(sender.active).toBe(true);
		scheduler.tick();
		scheduler.tick();
		sender.release();

		expect(sent).toEqual([
			{ linear: 0.2, angular: 0 },
			{ linear: 0.2, angular: 0 },
			{ linear: 0.2, angular: 0 },
			{ linear: 0, angular: 0 }
		]);
		expect(scheduler.running()).toBe(false);
		expect(sender.active).toBe(false);
	});

	it('sends changes immediately but not repeats of the same value', () => {
		const { sent, sender } = setup();
		sender.update({ linear: 0.2, angular: 0 });
		sender.update({ linear: 0.2, angular: 0 });
		sender.update({ linear: 0.3, angular: 0 });
		expect(sent.map((d) => d.linear)).toEqual([0.2, 0.3]);
	});

	it('does nothing on release when not driving', () => {
		const { sent, sender } = setup();
		sender.release();
		expect(sent).toEqual([]);
	});

	it('reports send errors without throwing', async () => {
		const onError = vi.fn();
		const sender = new MoveSender(
			async () => Promise.reject(new Error('offline')),
			200,
			fakeScheduler(),
			onError
		);
		sender.update({ linear: 0.1, angular: 0 });
		await vi.waitFor(() => expect(onError).toHaveBeenCalled());
	});

	it('uses real timers by default', () => {
		vi.useFakeTimers();
		const sent: Drive[] = [];
		const sender = new MoveSender(async (d) => void sent.push(d), 100);
		sender.update({ linear: 0.1, angular: 0 });
		vi.advanceTimersByTime(350);
		sender.release();
		vi.useRealTimers();
		expect(sent).toHaveLength(5); // first + 3 repeats + stop
	});
});
