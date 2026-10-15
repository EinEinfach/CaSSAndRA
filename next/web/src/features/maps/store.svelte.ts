// The list of maps for the UI, kept current by the "maps" event.
import type { EventStream } from '#shared/events.ts';
import type { GardenMap, MapList } from './types.ts';

export class MapsStore {
	maps = $state<GardenMap[]>([]);
	activeId = $state('');
	/** False until the first event arrived. */
	loaded = $state(false);

	readonly active = $derived(this.maps.find((m) => m.id === this.activeId) ?? null);

	/** Starts following the stream. Returns a function that stops it. */
	connect(stream: EventStream): () => void {
		return stream.on<MapList>('maps', (list) => this.apply(list));
	}

	apply(list: MapList): void {
		this.maps = list.maps;
		this.activeId = list.activeId;
		this.loaded = true;
	}

	byId(id: string): GardenMap | null {
		return this.maps.find((m) => m.id === id) ?? null;
	}
}
