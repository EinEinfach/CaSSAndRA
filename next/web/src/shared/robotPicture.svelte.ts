// The picture the map draws for the robot. The layout keeps it in line with
// the appearance settings; every MapCanvas below it uses it.
import { getContext, setContext } from 'svelte';
import type { RobotPicture } from './drawMap.ts';

export type ImageLoader = (src: string) => Promise<CanvasImageSource>;

export const loadImage: ImageLoader = (src) =>
	new Promise((resolve, reject) => {
		const img = new Image();
		img.onload = () => resolve(img);
		img.onerror = () => reject(new Error(`cannot load ${src}`));
		img.src = src;
	});

/** URL of a picture in static/rovers (taken from legacy CaSSAndRA). */
export const robotPictureURL = (name: string) => `/rovers/${name}.png`;

export class RobotPictureSource {
	/** Null until the image has loaded; the map draws an arrow until then. */
	current = $state.raw<RobotPicture | null>(null);
	private src = '';

	constructor(private load: ImageLoader = loadImage) {}

	/** Switches to picture name with an edge of sizeCm; loads each picture once. */
	async set(name: string, sizeCm: number): Promise<void> {
		const src = robotPictureURL(name);
		const sizeM = sizeCm / 100;
		if (src === this.src) {
			if (this.current) this.current = { ...this.current, sizeM };
			return;
		}
		this.src = src;
		try {
			const image = await this.load(src);
			if (this.src === src) this.current = { image, sizeM };
		} catch (err) {
			console.error(err);
			if (this.src === src) this.current = null;
		}
	}
}

const key = Symbol('robot picture');

export function provideRobotPicture(source: RobotPictureSource): void {
	setContext(key, source);
}

/** The layout's picture source, or null outside the layout (e.g. in tests). */
export function useRobotPicture(): RobotPictureSource | null {
	return getContext<RobotPictureSource | undefined>(key) ?? null;
}
