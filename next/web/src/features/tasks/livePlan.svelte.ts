// Planning a route from the live page: the whole garden or a drawn area with
// mow settings that are not saved, or saved tasks. Nothing moves until the
// route is calculated and "Start mowing" is pressed.
import type { MapInteraction } from '#shared/MapCanvas.svelte';
import { planMatchesParts, planMatchesTasks } from './plan.ts';
import { PlanSession } from './session.svelte.ts';
import type { Plan, PreviewRequest } from './types.ts';

/** What the route covers: a part of the garden drawn here, or saved tasks. */
export type LiveMode = 'area' | 'tasks';

/**
 * What the play button does. A choice in the open planner wins; without one an
 * interrupted route goes on, otherwise the whole garden is planned.
 */
export type PlayAction =
	{ kind: 'tasks' | 'area' | 'garden'; request: PreviewRequest } | { kind: 'resume' };

export function describePlay(action: PlayAction | null): string {
	if (!action) return 'Mow';
	switch (action.kind) {
		case 'resume':
			return 'Mow: the route on the robot';
		case 'tasks': {
			const n = action.request.taskIds!.length;
			return n === 1 ? 'Mow: the chosen task' : `Mow: the ${n} chosen tasks`;
		}
		case 'area':
			return 'Mow: the drawn area';
		case 'garden':
			return 'Mow: the whole garden';
	}
}

export class LivePlan {
	open = $state(false);
	mode = $state<LiveMode>('area');
	readonly session = new PlanSession();

	private adopted = false;

	/** The request for the route; null while the choice is incomplete. */
	get request(): PreviewRequest | null {
		if (this.mode === 'tasks') {
			return this.session.chosen.length > 0 ? { taskIds: [...this.session.chosen] } : null;
		}
		const parts = this.session.drafted;
		return parts ? { parts } : null;
	}

	/** A part drawn on the Tasks page with more parts is kept but not edited here. */
	get editable(): boolean {
		return this.session.parts.length <= 1;
	}

	/** Whether the map draws a selection while the planner is open. */
	get drawing(): boolean {
		return this.open && this.mode === 'area' && this.editable && this.session.tool !== 'all';
	}

	/**
	 * The play button's action; null until the mow settings are known.
	 * resumable: the robot holds a route it left before the end. Without an
	 * active map there is nothing to plan: the robot mows the route it has.
	 */
	play(resumable: boolean, hasMap = true): PlayAction | null {
		const chosen = this.open ? this.request : null;
		if (chosen?.taskIds) return { kind: 'tasks', request: chosen };
		if (chosen?.parts && (!this.editable || this.session.tool !== 'all')) {
			return { kind: 'area', request: chosen };
		}
		if (resumable || !hasMap) return { kind: 'resume' };
		const p = this.session.parts[0];
		if (!p) return null;
		return {
			kind: 'garden',
			request: { parts: [{ selection: [], parameters: $state.snapshot(p.parameters) }] }
		};
	}

	/** Whether plan was calculated for exactly the current choice. */
	matches(plan: Plan): boolean {
		if (this.mode === 'tasks') return planMatchesTasks(plan, this.session.chosen);
		const parts = this.session.drafted;
		return parts !== null && planMatchesParts(plan, parts);
	}

	/** Takes over what was planned before the page opened (here or on the Tasks page), once. */
	adopt(plan: Plan | null): void {
		if (this.adopted) return;
		this.adopted = true;
		this.session.adopt(plan);
		if (plan && plan.taskIds.length > 0) this.mode = 'tasks';
	}

	start(): void {
		this.open = true;
	}

	close(): void {
		this.open = false;
	}

	/** Back to one part over the whole garden with the default settings. */
	startOver(): void {
		this.session.reset();
	}

	readonly interact: MapInteraction = {
		tap: (p) => this.session.tap(p),
		press: (p, mpp) => this.session.press(p, mpp),
		move: (p) => this.session.move(p),
		release: () => this.session.release()
	};
}
