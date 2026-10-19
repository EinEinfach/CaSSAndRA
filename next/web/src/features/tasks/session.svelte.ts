// State of planning a route: the chosen part of the garden and the parameters.
import type { MapLayers } from '#shared/drawMap.ts';
import type { Point } from '#shared/viewport.ts';
import { hit, isUsable, rectangle, roundPoint, type Tool } from './selection.ts';
import type { Parameters, Plan, PreviewRequest } from './types.ts';

/** How close (in screen pixels) a pointer must be to grab a corner. */
export const GRAB_PX = 14;

export class PlanSession {
	tool = $state<Tool>('all');
	/** Corners of the selection; while dragging a rectangle, the current one. */
	selection = $state.raw<Point[]>([]);
	/** Bound to the form; null until defaults or a plan arrived. */
	parameters = $state<Parameters | null>(null);

	private rectFrom: Point | null = null;
	private dragged: number | null = null;
	private adopted = false;

	readonly request: PreviewRequest | null = $derived(
		this.parameters && (this.tool === 'all' || isUsable(this.selection))
			? {
					selection: this.tool === 'all' ? [] : this.selection,
					parameters: $state.snapshot(this.parameters)
				}
			: null
	);

	/** The planner settings, unless parameters are set already. */
	useDefaults(p: Parameters): void {
		if (this.parameters === null) this.parameters = { ...p };
	}

	/**
	 * Shows what was planned when the page opens: only the first plan event
	 * counts, later ones come from this page or another browser.
	 */
	adopt(plan: Plan | null): void {
		if (this.adopted) return;
		this.adopted = true;
		if (!plan) return;
		this.parameters = { ...plan.parameters };
		this.selection = plan.selection;
		this.tool = plan.selection.length > 0 ? 'polygon' : 'all';
	}

	/** Switching keeps a selection as polygon, so its corners can be moved. */
	setTool(tool: Tool): void {
		if (tool === 'all' || (tool === 'rectangle' && this.tool !== 'rectangle')) {
			this.selection = [];
		}
		this.tool = tool;
	}

	clearSelection(): void {
		this.selection = [];
	}

	removeLastCorner(): void {
		this.selection = this.selection.slice(0, -1);
	}

	/** Polygon: a tap adds a corner. */
	tap(world: Point): void {
		if (this.tool === 'polygon') this.selection = [...this.selection, roundPoint(world)];
	}

	/** Rectangle: starts a new one. Polygon: grabs a corner. Otherwise the map pans. */
	press(world: Point, metersPerPixel: number): boolean {
		if (this.tool === 'rectangle') {
			this.rectFrom = world;
			this.selection = [];
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
			this.selection = rectangle(this.rectFrom, world);
		} else if (this.dragged !== null) {
			const i = this.dragged;
			this.selection = this.selection.map((p, j) => (j === i ? roundPoint(world) : p));
		}
	}

	release(): void {
		if (this.rectFrom && !isUsable(this.selection)) this.selection = [];
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
