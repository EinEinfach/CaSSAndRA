<script lang="ts">
	// Choosing what the play button mows (legacy "mow all or selected area" and
	// "select task"); the route can be previewed before.
	import AreaTools from './AreaTools.svelte';
	import type { LivePlan } from './livePlan.svelte.ts';
	import ParametersForm from './ParametersForm.svelte';
	import { formatDistance, formatDuration } from './plan.ts';
	import TaskList from './TaskList.svelte';
	import type { Plan, PreviewRequest, Task } from './types.ts';

	let {
		live,
		plan,
		tasks,
		mowSpeedMps,
		playLabel,
		hasMap,
		preview,
		discard
	}: {
		live: LivePlan;
		/** The plan for the active map, if there is one. */
		plan: Plan | null;
		/** Saved tasks of the active map. */
		tasks: Task[];
		mowSpeedMps: number;
		/** What the play button does now, e.g. "Mow: the drawn area". */
		playLabel: string;
		hasMap: boolean;
		preview: (req: PreviewRequest) => Promise<unknown>;
		discard: () => Promise<void>;
	} = $props();

	type Action = 'calculate' | 'discard';
	let busy = $state<Action | null>(null);
	let error = $state('');

	const request = $derived(live.request);
	const current = $derived(plan !== null && live.matches(plan));

	async function run(what: Action, action: () => Promise<unknown>) {
		busy = what;
		error = '';
		try {
			await action();
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = null;
		}
	}
</script>

<section class="planner" aria-label="Plan mowing">
	{#if !live.open}
		<button type="button" disabled={!hasMap} onclick={() => live.start()}>Plan mowing</button>
		{#if !hasMap}
			<p class="hint">Choose or draw a map under Maps to plan a route.</p>
		{/if}
	{:else}
		<div class="head">
			<h2>Plan mowing</h2>
			<button type="button" class="link" onclick={() => live.close()}>Close</button>
		</div>
		<div class="segmented" role="radiogroup" aria-label="Mow">
			<label class:selected={live.mode === 'area'}>
				<input type="radio" name="live-mode" value="area" bind:group={live.mode} />
				Garden or area
			</label>
			<label class:selected={live.mode === 'tasks'}>
				<input type="radio" name="live-mode" value="tasks" bind:group={live.mode} />
				Saved tasks
			</label>
		</div>

		{#if live.mode === 'tasks'}
			<TaskList
				{tasks}
				chosen={live.session.chosen}
				busy={busy !== null}
				toggle={(id) => live.session.toggle(id)}
				empty="No saved tasks for this map. Create them under Tasks."
			/>
		{:else if !live.editable}
			<p class="hint">
				This route has {live.session.parts.length} parts from the Tasks page.
				<button type="button" class="link" onclick={() => live.startOver()}>Start over</button>
			</p>
		{:else if live.session.part}
			<AreaTools session={live.session} />
			<details>
				<summary>Mow settings</summary>
				<p class="hint">Only for this route; the defaults stay as in Settings.</p>
				<div class="settings">
					<ParametersForm parameters={live.session.part.parameters} />
				</div>
			</details>
		{/if}

		<p class="play" role="status">▶ {playLabel.replace(/^Mow: /, 'mows ')}</p>
		<button
			type="button"
			disabled={busy !== null || request === null}
			onclick={() => run('calculate', () => preview(request!))}
		>
			{busy === 'calculate' ? 'Calculating…' : 'Calculate route'}
		</button>
		{#if request === null}
			<p class="hint">
				{live.mode === 'tasks'
					? 'Choose tasks to mow only them.'
					: 'Draw the area on the map to mow only it.'}
			</p>
		{/if}

		{#if plan}
			<div class="result" aria-label="Planned route">
				<strong>{formatDistance(plan.distanceM)}</strong>
				<span>{plan.route.length} points</span>
				{#if formatDuration(plan.distanceM, mowSpeedMps)}
					<span>about {formatDuration(plan.distanceM, mowSpeedMps)}</span>
				{/if}
			</div>
			{#if !current}
				<p class="hint">The choice changed since. Calculate again to see its route.</p>
			{/if}
			<button type="button" disabled={busy !== null} onclick={() => run('discard', discard)}>
				Discard route
			</button>
		{/if}
	{/if}
	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
</section>

<style>
	.planner {
		display: grid;
		gap: 10px;
	}
	.head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
	}
	details {
		display: grid;
		gap: 10px;
	}
	summary {
		cursor: pointer;
		font-weight: 600;
		font-size: 0.9rem;
	}
	.settings {
		display: flex;
		flex-direction: column;
		gap: 10px;
		margin-top: 10px;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.link {
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
	.play {
		margin: 0;
		font-weight: 600;
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
