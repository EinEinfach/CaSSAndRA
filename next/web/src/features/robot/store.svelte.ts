// Live robot state for the UI, fed by the event stream.
import type { EventStream } from '#shared/events.ts';
import type { Point } from '#shared/viewport.ts';
import { clearTrail, fetchMap, fetchTrail } from './api.ts';
import { extendTrail } from './trail.ts';
import type { RobotMap, RobotState, Trail } from './types.ts';

/** Where the trail lives: the backend keeps it, the store follows it. */
export interface TrailApi {
	load(): Promise<Trail>;
	clear(): Promise<void>;
}

const backendTrail: TrailApi = { load: () => fetchTrail(), clear: () => clearTrail() };

const emptyMap: RobotMap = { perimeter: [], exclusions: [], dock: [], way: [] };

export class RobotStore {
	state = $state<RobotState | null>(null);
	map = $state<RobotMap>(emptyMap);
	trail = $state<Point[]>([]);
	connected = $state(false);

	private loadedCrc: number | null = null;
	private trailId: number | null = null;
	private stops: (() => void)[] = [];

	constructor(
		private loadMap: () => Promise<RobotMap> = () => fetchMap(),
		private trailApi: TrailApi = backendTrail
	) {}

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
		if (s.trailId !== this.trailId) {
			// A new trail (docked, cleared, or first state): take the backend's.
			this.trailId = s.trailId;
			this.trail = [];
			this.loadTrail();
		} else if (s.status !== 'offline') {
			// Same trail: extend it like the backend does instead of fetching it all again.
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

	/** Starts a new trail for every browser. */
	async clearTrail(): Promise<void> {
		this.trail = [];
		await this.trailApi.clear();
	}

	private loadTrail(): void {
		const id = this.trailId;
		this.trailApi
			.load()
			.then((t) => {
				if (t.id !== id || this.trailId !== id) return; // a newer trail is coming
				// Keep what states added while loading.
				this.trail = this.trail.reduce((trail, p) => extendTrail(trail, p), t.points);
			})
			.catch((err) => {
				console.error('loading the trail failed', err);
				if (this.trailId === id) this.trailId = null; // retry with the next state
			});
	}
}
