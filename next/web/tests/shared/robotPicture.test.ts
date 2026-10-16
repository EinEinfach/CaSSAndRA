import { describe, expect, it, vi } from 'vitest';
import { RobotPictureSource, robotPictureURL } from '#shared/robotPicture.svelte.ts';

/** A loader whose images arrive when the test resolves them. */
function deferredLoader() {
	const pending = new Map<
		string,
		{ resolve: (img: CanvasImageSource) => void; reject: (e: Error) => void }
	>();
	const load = vi.fn(
		(src: string) =>
			new Promise<CanvasImageSource>((resolve, reject) => pending.set(src, { resolve, reject }))
	);
	const image = (src: string) => ({ src }) as unknown as CanvasImageSource;
	return {
		load,
		image,
		resolve: (src: string) => pending.get(src)!.resolve(image(src)),
		reject: (src: string) => pending.get(src)!.reject(new Error('404'))
	};
}

describe('RobotPictureSource', () => {
	it('loads the picture from static/rovers and keeps its size in meters', async () => {
		const loader = deferredLoader();
		const source = new RobotPictureSource(loader.load);

		const done = source.set('alfred', 130);
		expect(source.current).toBeNull();
		loader.resolve('/rovers/alfred.png');
		await done;

		expect(loader.load).toHaveBeenCalledWith(robotPictureURL('alfred'));
		expect(source.current).toEqual({ image: loader.image('/rovers/alfred.png'), sizeM: 1.3 });
	});

	it('changes only the size without loading again', async () => {
		const loader = deferredLoader();
		const source = new RobotPictureSource(loader.load);
		const first = source.set('default', 100);
		loader.resolve('/rovers/default.png');
		await first;

		await source.set('default', 250);

		expect(loader.load).toHaveBeenCalledTimes(1);
		expect(source.current?.sizeM).toBe(2.5);
	});

	it('keeps the picture chosen last when an earlier one loads later', async () => {
		const loader = deferredLoader();
		const source = new RobotPictureSource(loader.load);
		const slow = source.set('alfred', 100);
		const fast = source.set('ardumower', 100);

		loader.resolve('/rovers/ardumower.png');
		await fast;
		loader.resolve('/rovers/alfred.png');
		await slow;

		expect(source.current?.image).toEqual(loader.image('/rovers/ardumower.png'));
	});

	it('falls back to no picture when loading fails', async () => {
		vi.spyOn(console, 'error').mockImplementation(() => {});
		const loader = deferredLoader();
		const source = new RobotPictureSource(loader.load);
		const ok = source.set('default', 100);
		loader.resolve('/rovers/default.png');
		await ok;

		const broken = source.set('landrumower', 100);
		loader.reject('/rovers/landrumower.png');
		await broken;

		expect(source.current).toBeNull();
		vi.restoreAllMocks();
	});
});
