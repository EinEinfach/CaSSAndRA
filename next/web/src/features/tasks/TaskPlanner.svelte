<script lang="ts">
	import MapCanvas, { type MapInteraction } from '#shared/MapCanvas.svelte';
	import MapLayout from '#shared/MapLayout.svelte';
	import type { MapLayers, RobotPose } from '#shared/drawMap.ts';
	import type { GardenMap } from '#features/maps/types.ts';
	import type { RobotStatus } from '#features/robot/types.ts';
	import PartForm from './PartForm.svelte';
	import {
		canStartRoute,
		formatDistance,
		formatDuration,
		planMatchesParts,
		planMatchesTasks
	} from './plan.ts';
	import { PlanSession } from './session.svelte.ts';
	import TaskList from './TaskList.svelte';
	import type { Parameters, Plan, PreviewRequest, Task, TaskShape } from './types.ts';

	let {
		map,
		robot = null,
		tasks,
		plan,
		planLoaded,
		defaults,
		mowSpeedMps,
		robotStatus,
		preview,
		discard,
		start,
		save,
		remove
	}: {
		/** The active map; null = none. */
		map: GardenMap | null;
		robot?: RobotPose | null;
		/** Saved tasks of the active map. */
		tasks: Task[];
		plan: Plan | null;
		/** True once the plan event arrived, so the page can show the last plan. */
		planLoaded: boolean;
		defaults: Parameters | null;
		mowSpeedMps: number;
		robotStatus: RobotStatus;
		preview: (req: PreviewRequest) => Promise<unknown>;
		discard: () => Promise<void>;
		/** Sends the route to the robot and starts mowing. */
		start: () => Promise<void>;
		/** Creates (id null) or changes a saved task. */
		save: (task: TaskShape, id: string | null) => Promise<unknown>;
		remove: (id: string) => Promise<void>;
	} = $props();

	type Action = 'plan' | 'calculate' | 'save' | 'delete' | 'start' | 'discard';

	const session = new PlanSession();
	let busy = $state<Action | null>(null);
	let error = $state('');
	let saved = $state('');

	$effect(() => {
		if (planLoaded) session.adopt(plan);
	});
	$effect(() => {
		if (defaults) session.useDefaults(defaults);
	});
	$effect(() => {
		const ids = tasks.map((t) => t.id);
		session.keepChosen(ids);
	});

	const shownPlan = $derived(plan && map && plan.mapId === map.id ? plan : null);
	const outdated = $derived.by(() => {
		if (!shownPlan) return false;
		if (shownPlan.taskIds.length > 0) return !planMatchesTasks(shownPlan, session.chosen);
		return session.drafted !== null && !planMatchesParts(shownPlan, session.drafted);
	});
	const startable = $derived(shownPlan !== null && !outdated && canStartRoute(robotStatus));
	const task = $derived(map ? session.toTask(map.id) : null);

	const interact: MapInteraction = {
		tap: (p) => session.tap(p),
		press: (p, mpp) => session.press(p, mpp),
		move: (p) => session.move(p),
		release: () => session.release()
	};

	const layers: MapLayers = $derived({
		perimeter: map?.perimeter ?? [],
		exclusions: map?.exclusions ?? [],
		dock: map?.dock ?? [],
		searchWire: map?.searchWire ?? [],
		way: shownPlan?.route ?? [],
		robot,
		...session.canvasLayers
	});

	async function run(what: Action, action: () => Promise<unknown>) {
		error = '';
		saved = '';
		busy = what;
		try {
			await action();
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = null;
		}
	}

	async function saveTask() {
		const name = task!.name;
		await save(task!, session.editing);
		session.reset();
		saved = `Saved ${name}.`;
	}
</script>

<MapLayout label="Plan a route">
	{#snippet map()}
		<MapCanvas
			{layers}
			label="Map for planning a route"
			interact={session.tool === 'all' ? undefined : interact}
		/>
	{/snippet}
	{#snippet panel()}
		{#if !map}
			<p class="empty">No active map. Choose or draw one under Maps.</p>
		{:else}
			<section aria-label="Saved tasks">
				<h2>Saved tasks</h2>
				<TaskList
					{tasks}
					chosen={session.chosen}
					busy={busy !== null}
					toggle={(id) => session.toggle(id)}
					edit={(t) => session.edit(t)}
					remove={(id) => run('delete', () => remove(id))}
				/>
				{#if tasks.length > 0}
					<button
						type="button"
						class:primary={session.chosen.length > 0 && (!shownPlan || outdated)}
						disabled={busy !== null || session.chosen.length === 0}
						onclick={() => run('plan', () => preview({ taskIds: session.chosen }))}
					>
						{busy === 'plan'
							? 'Calculating…'
							: session.chosen.length > 1
								? `Plan ${session.chosen.length} tasks`
								: 'Plan task'}
					</button>
				{/if}
			</section>

			<section aria-label="Task editor">
				<h2>{session.editing ? `Edit ${session.name || 'task'}` : 'New task'}</h2>
				<PartForm {session} />
				<button
					type="button"
					disabled={busy !== null || session.drafted === null}
					onclick={() => run('calculate', () => preview({ parts: session.drafted! }))}
				>
					{busy === 'calculate' ? 'Calculating…' : 'Calculate route'}
				</button>
				{#if session.part && session.drafted === null}
					<p class="hint">Select an area for every part first.</p>
				{/if}
				<div class="save">
					<input
						class="text"
						aria-label="Task name"
						placeholder="Name of the task"
						bind:value={session.name}
					/>
					<button
						type="button"
						disabled={busy !== null || task === null}
						onclick={() => run('save', saveTask)}
					>
						{session.editing ? 'Save changes' : 'Save task'}
					</button>
				</div>
				{#if session.editing}
					<button type="button" class="link" onclick={() => session.reset()}>
						Stop editing, start a new task
					</button>
				{/if}
				{#if saved}
					<p class="hint" role="status">{saved}</p>
				{/if}
			</section>

			<section aria-label="Route">
				{#if shownPlan}
					<div class="result" aria-label="Planned route">
						<strong>{formatDistance(shownPlan.distanceM)}</strong>
						<span>{shownPlan.route.length} points</span>
						{#if formatDuration(shownPlan.distanceM, mowSpeedMps)}
							<span>about {formatDuration(shownPlan.distanceM, mowSpeedMps)}</span>
						{/if}
					</div>
					{#if outdated}
						<p class="hint">The choice changed since. Calculate again to update the route.</p>
					{/if}
					<button
						type="button"
						class:primary={!outdated}
						disabled={busy !== null || !startable}
						onclick={() => run('start', start)}
					>
						{busy === 'start' ? 'Sending route…' : 'Start mowing'}
					</button>
					{#if !outdated && !canStartRoute(robotStatus)}
						<p class="hint">The robot can start when it is idle or in the dock.</p>
					{/if}
					<button type="button" disabled={busy !== null} onclick={() => run('discard', discard)}>
						Discard route
					</button>
				{/if}
				{#if error}
					<p class="error" role="alert">{error}</p>
				{/if}
			</section>
		{/if}
	{/snippet}
</MapLayout>

<style>
	section {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
	}
	.hint,
	.empty {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.save {
		display: flex;
		gap: 8px;
	}
	.save input {
		flex: 1;
		min-width: 0;
	}
	.link {
		align-self: flex-start;
		border: none;
		background: none;
		padding: 0;
		color: var(--text-muted);
		text-decoration: underline;
		font-size: 0.85rem;
	}
	.result {
		display: flex;
		flex-wrap: wrap;
		gap: 4px 12px;
		align-items: baseline;
	}
	.result span {
		color: var(--text-muted);
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
