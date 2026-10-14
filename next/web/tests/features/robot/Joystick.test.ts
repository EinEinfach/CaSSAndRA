import { fireEvent, render, screen } from '@testing-library/svelte';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Joystick from '#features/robot/Joystick.svelte';
import { MoveSender, type Drive, type Scheduler } from '#features/robot/drive.ts';

const noTimer: Scheduler = { setInterval: () => 1, clearInterval: () => {} };

function setup(disabled = false) {
	const sent: Drive[] = [];
	const sender = new MoveSender(async (d) => void sent.push(d), 200, noTimer);
	const view = render(Joystick, { disabled, sender });
	const pad = screen.getByRole('slider');
	// 160 x 160 pad at the origin: center (80,80), usable radius 60 px.
	pad.getBoundingClientRect = () => ({ left: 0, top: 0, width: 160, height: 160 }) as DOMRect;
	return { sent, pad, view };
}

// jsdom has no PointerEvent constructor with coordinates; MouseEvent carries them.
const pointer = (type: string, x: number, y: number, pointerId = 1) => {
	const e = new MouseEvent(type, { clientX: x, clientY: y, bubbles: true });
	Object.defineProperty(e, 'pointerId', { value: pointerId });
	return e;
};

beforeEach(() => {
	vi.restoreAllMocks();
});

describe('Joystick', () => {
	it('drives forward when dragged up and stops on release', async () => {
		const { sent, pad } = setup();

		await fireEvent(pad, pointer('pointerdown', 80, 20));
		await fireEvent(pad, pointer('pointerup', 80, 20));

		expect(sent).toEqual([
			{ linear: 0.5, angular: 0 },
			{ linear: 0, angular: 0 }
		]);
	});

	it('follows the finger and clamps to the edge', async () => {
		const { sent, pad } = setup();
		await fireEvent(pad, pointer('pointerdown', 80, 80));
		await fireEvent(pad, pointer('pointermove', 0, 80));
		await fireEvent(pad, pointer('pointerup', 0, 80));

		expect(sent.map((d) => d.angular)).toEqual([0, 1, 0]);
	});

	it('ignores a second finger', async () => {
		const { sent, pad } = setup();
		await fireEvent(pad, pointer('pointerdown', 80, 20, 1));
		await fireEvent(pad, pointer('pointermove', 80, 140, 2));
		await fireEvent(pad, pointer('pointerup', 80, 140, 2));
		expect(sent).toEqual([{ linear: 0.5, angular: 0 }]);
	});

	it('does nothing when disabled', async () => {
		const { sent, pad } = setup(true);
		await fireEvent(pad, pointer('pointerdown', 80, 20));
		expect(sent).toEqual([]);
		expect(pad.getAttribute('aria-disabled')).toBe('true');
	});

	it('stops the robot when it disappears mid-drive', async () => {
		const { sent, pad, view } = setup();
		await fireEvent(pad, pointer('pointerdown', 80, 20));
		view.unmount();
		expect(sent.at(-1)).toEqual({ linear: 0, angular: 0 });
	});
});
