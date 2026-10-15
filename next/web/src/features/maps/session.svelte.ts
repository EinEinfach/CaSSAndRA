// State of one map editing session: what is drawn, selected and undoable.
import type { MapLayers } from '#shared/drawMap.ts';
import type { Point } from '#shared/viewport.ts';
import {
	History,
	addExclusion,
	addPoint,
	clearLayer,
	hitPoint,
	isClosed,
	movePoint,
	perimeterLayer,
	pointsOf,
	problems,
	removePoint,
	sameLayer,
	type Layer
} from './editor.ts';
import type { MapShape } from './types.ts';

/** How close (in screen pixels) a pointer must be to grab a point. */
export const GRAB_PX = 14;

export class EditorSession {
	/** The geometry; its name is ignored, see name. */
	draft = $state.raw<MapShape>(null!);
	/** The name is not part of the undo history. */
	name = $state('');
	layer = $state.raw<Layer>(perimeterLayer);
	selected = $state<number | null>(null);
	private revision = $state(0); // bumps on every history change, for canUndo/canRedo

	private history: History<MapShape>;
	private dragFrom: MapShape | null = null;

	readonly problems = $derived(problems(this.result));

	constructor(initial: MapShape) {
		this.history = new History(initial);
		this.draft = initial;
		this.name = initial.name;
	}

	get canUndo(): boolean {
		void this.revision; // reactive: history itself is not
		return this.history.canUndo;
	}

	get canRedo(): boolean {
		void this.revision;
		return this.history.canRedo;
	}

	/** The map to save. */
	get result(): MapShape {
		return { ...this.draft, name: this.name };
	}

	/** Layers for MapCanvas, with handles on the edited layer. */
	get canvasLayers(): MapLayers {
		return {
			perimeter: this.draft.perimeter,
			exclusions: this.draft.exclusions,
			dock: this.draft.dock,
			searchWire: this.draft.searchWire,
			edit: {
				points: pointsOf(this.draft, this.layer),
				closed: isClosed(this.layer),
				selected: this.selected
			}
		};
	}

	private commit(next: MapShape) {
		this.history.push(next);
		this.draft = next;
		this.revision++;
	}

	selectLayer(layer: Layer): void {
		this.layer = layer;
		this.selected = null;
	}

	isLayer(layer: Layer): boolean {
		return sameLayer(this.layer, layer);
	}

	/** A tap selects the point under the pointer or adds one to the layer. */
	tap(world: Point, metersPerPixel: number): void {
		const hit = hitPoint(this.draft, world, GRAB_PX * metersPerPixel, this.layer);
		if (hit) {
			this.layer = hit.layer;
			this.selected = hit.index;
			return;
		}
		this.add(world);
	}

	add(world: Point): void {
		const { map, index } = addPoint(this.draft, this.layer, world);
		this.commit(map);
		this.selected = index;
	}

	/** Grabs the point under the pointer for dragging. */
	press(world: Point, metersPerPixel: number): boolean {
		const hit = hitPoint(this.draft, world, GRAB_PX * metersPerPixel, this.layer);
		if (!hit) return false;
		this.layer = hit.layer;
		this.selected = hit.index;
		this.dragFrom = this.draft;
		return true;
	}

	move(world: Point): void {
		if (this.dragFrom === null || this.selected === null) return;
		this.draft = movePoint(this.draft, this.layer, this.selected, world);
	}

	/** Ends a drag; the whole drag is one undo step. */
	release(): void {
		if (this.dragFrom === null) return;
		const moved = this.draft;
		this.draft = this.dragFrom;
		this.dragFrom = null;
		if (moved !== this.draft) this.commit(moved);
	}

	deleteSelected(): void {
		if (this.selected === null) return;
		const next = removePoint(this.draft, this.layer, this.selected);
		const left = pointsOf(next, this.layer).length;
		this.commit(next);
		this.selected = left === 0 ? null : Math.min(this.selected, left - 1);
	}

	newExclusion(): void {
		const { map, layer } = addExclusion(this.draft);
		this.commit(map);
		this.selectLayer(layer);
	}

	/** Removes the edited exclusion, or empties the edited line or perimeter. */
	clear(): void {
		this.commit(clearLayer(this.draft, this.layer));
		if (this.layer.kind === 'exclusion') this.layer = perimeterLayer;
		this.selected = null;
	}

	undo(): void {
		this.draft = this.history.undo();
		this.afterTimeTravel();
	}

	redo(): void {
		this.draft = this.history.redo();
		this.afterTimeTravel();
	}

	private afterTimeTravel() {
		this.revision++;
		this.selected = null;
		if (this.layer.kind === 'exclusion' && this.layer.index >= this.draft.exclusions.length) {
			this.layer = perimeterLayer;
		}
	}
}
