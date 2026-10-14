// Live robot state for the UI, fed by the event stream.
import type { EventStream } from '#shared/events.ts';
import type { Point } from '#shared/viewport.ts';
import { fetchMap } from './api.ts';
import { extendTrail } from './trail.ts';
import type { RobotMap, RobotState } from './types.ts';

const emptyMap: RobotMap = { perimeter: [], exclusions: [], dock: [], way: [] };

export class RobotStore {
	state = $state<RobotState | null>(null);
	map = $state<RobotMap>(emptyMap);
	trail = $state<Point[]>([]);
	connected = $state(false);

	private loadedCrc: number | null = null;
	private stops: (() => void)[] = [];

	constructor(private loadMap: () => Promise<RobotMap> = () => fetchMap()) {}

	/** Starts following the stream. Returns a function that stops it. */
	connect(stream: EventStream): () => void {
		this.stops.push(
			stream.on<RobotState>('robot', (s) => this.apply(s)),
			stream.onStatus((c) => (this.connected = c))
		);
		return () => this.disconnect();
	}

	disconnect(): void {
		for (const stop of this.stops) stop();
		this.stops = [];
	}

	apply(s: RobotState): void {
		this.state = s;
		if (s.status !== 'offline') {
			this.trail = extendTrail(this.trail, s.position);
		}
		if (s.mapCrc !== this.loadedCrc) {
			this.loadedCrc = s.mapCrc;
			this.loadMap()
				.then((m) => (this.map = m))
				.catch((err) => {
					console.error('loading robot map failed', err);
					this.loadedCrc = null; // retry with the next state
				});
		}
	}

	clearTrail(): void {
		this.trail = [];
	}
}
