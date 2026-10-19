// State of the tasks page: the task being drawn (its parts, each an area and
// parameters) and the saved tasks chosen for planning.
import type { MapLayers } from '#shared/drawMap.ts';
import type { Point } from '#shared/viewport.ts';
import { hit, isUsable, rectangle, roundPoint, type Tool } from './selection.ts';
import type { Parameters, Part, Plan, Task, TaskShape } from './types.ts';

/** How close (in screen pixels) a pointer must be to grab a corner. */
export const GRAB_PX = 14;

/** A part while it is drawn. */
export interface PartDraft {
	tool: Tool;
	/** Corners of the selection; while dragging a rectangle, the current one. */
	selection: Point[];
	/** Bound to the form. */
	parameters: Parameters;
}

const toolOf = (selection: Point[]): Tool => (selection.length > 0 ? 'polygon' : 'all');

const draftOf = (p: Part): PartDraft => ({
	tool: toolOf(p.selection),
	selection: p.selection,
	parameters: { ...p.parameters }
});

export class PlanSession {
	parts = $state<PartDraft[]>([]);
	current = $state(0);
	/** Name for saving; editing is the ID of the saved task being changed. */
	name = $state('');
	editing = $state<string | null>(null);
	/** Saved tasks chosen for planning, in the order they are mowed. */
	chosen = $state<string[]>([]);

	private defaults: Parameters | null = null;
	private rectFrom: Point | null = null;
	private dragged: number | null = null;
	private adopted = false;

	/** The part shown in the form and on the map; null until defaults arrived. */
	get part(): PartDraft | null {
		return this.parts[this.current] ?? null;
	}

	get tool(): Tool {
		return this.part?.tool ?? 'all';
	}

	get selection(): Point[] {
		return this.part?.selection ?? [];
	}

	private setSelection(pts: Point[]): void {
		if (this.part) this.part.selection = pts;
	}

	/** The drawn parts as the backend takes them; null while one is not usable. */
	readonly drafted: Part[] | null = $derived.by(() => {
		if (this.parts.length === 0) return null;
		const parts: Part[] = [];
		for (const p of this.parts) {
			if (p.tool !== 'all' && !isUsable(p.selection)) return null;
			parts.push({
				selection: p.tool === 'all' ? [] : $state.snapshot(p.selection),
				parameters: $state.snapshot(p.parameters)
			});
		}
		return parts;
	});

	/** The planner settings start every new part. */
	useDefaults(p: Parameters): void {
		this.defaults = { ...p };
		if (this.parts.length === 0) this.parts = [this.newPart()];
	}

	private newPart(): PartDraft {
		return { tool: 'all', selection: [], parameters: { ...this.defaults! } };
	}

	/**
	 * Shows what was planned when the page opens: only the first plan event
	 * counts, later ones come from this page or another browser.
	 */
	adopt(plan: Plan | null): void {
		if (this.adopted) return;
		this.adopted = true;
		if (!plan) return;
		if (plan.taskIds.length > 0) {
			this.chosen = [...plan.taskIds];
		} else {
			this.parts = plan.parts.map(draftOf);
			this.current = 0;
		}
	}

	// --- parts -------------------------------------------------------------

	selectPart(i: number): void {
		if (i >= 0 && i < this.parts.length) this.current = i;
	}

	/** A new part with the parameters of the current one. */
	addPart(): void {
		if (!this.part) return;
		this.parts.push({ tool: 'all', selection: [], parameters: { ...this.part.parameters } });
		this.current = this.parts.length - 1;
	}

	removePart(): void {
		if (this.parts.length < 2) return;
		this.parts.splice(this.current, 1);
		this.current = Math.min(this.current, this.parts.length - 1);
	}

	// --- saved tasks ---------------------------------------------------------

	/** Loads a saved task into the form to change it. */
	edit(task: Task): void {
		this.parts = task.parts.map(draftOf);
		this.current = 0;
		this.name = task.name;
		this.editing = task.id;
	}

	/** Starts a new task from the defaults. */
	reset(): void {
		this.parts = this.defaults ? [this.newPart()] : [];
		this.current = 0;
		this.name = '';
		this.editing = null;
	}

	/** The task to save, or null while a part or the name is missing. */
	toTask(mapId: string): TaskShape | null {
		const parts = this.drafted;
		const name = this.name.trim();
		return parts && name ? { name, mapId, parts } : null;
	}

	/** Adds a task to the end of the chosen ones, or takes it out. */
	toggle(id: string): void {
		this.chosen = this.chosen.includes(id)
			? this.chosen.filter((c) => c !== id)
			: [...this.chosen, id];
	}

	/** Drops chosen tasks that no longer exist (deleted, other map). */
	keepChosen(existing: string[]): void {
		const next = this.chosen.filter((id) => existing.includes(id));
		if (next.length !== this.chosen.length) this.chosen = next;
	}

	// --- drawing the area of the current part --------------------------------

	/** Switching keeps a selection as polygon, so its corners can be moved. */
	setTool(tool: Tool): void {
		const p = this.part;
		if (!p) return;
		if (tool === 'all' || (tool === 'rectangle' && p.tool !== 'rectangle')) p.selection = [];
		p.tool = tool;
	}

	clearSelection(): void {
		this.setSelection([]);
	}

	removeLastCorner(): void {
		this.setSelection(this.selection.slice(0, -1));
	}

	/** Polygon: a tap adds a corner. */
	tap(world: Point): void {
		if (this.tool === 'polygon') this.setSelection([...this.selection, roundPoint(world)]);
	}

	/** Rectangle: starts a new one. Polygon: grabs a corner. Otherwise the map pans. */
	press(world: Point, metersPerPixel: number): boolean {
		if (this.tool === 'rectangle') {
			this.rectFrom = world;
			this.setSelection([]);
			return true;
		}
		if (this.tool === 'polygon') {
			const i = hit(this.selection, world, GRAB_PX * metersPerPixel);
			if (i < 0) return false;
			this.dragged = i;
			return true;
		}
		return false;
	}

	move(world: Point): void {
		if (this.rectFrom) {
			this.setSelection(rectangle(this.rectFrom, world));
		} else if (this.dragged !== null) {
			const i = this.dragged;
			this.setSelection(this.selection.map((p, j) => (j === i ? roundPoint(world) : p)));
		}
	}

	release(): void {
		if (this.rectFrom && !isUsable(this.selection)) this.setSelection([]);
		this.rectFrom = null;
		this.dragged = null;
	}

	/** The selection for MapCanvas, with corner handles while drawing a polygon. */
	get canvasLayers(): Pick<MapLayers, 'selection' | 'edit'> {
		return {
			selection: this.tool === 'all' ? [] : this.selection,
			edit:
				this.tool === 'polygon' && this.selection.length > 0
					? { points: this.selection, closed: true, selected: null }
					: null
		};
	}
}
