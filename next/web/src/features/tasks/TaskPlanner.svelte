<script lang="ts">
	import MapCanvas, { type MapInteraction } from '#shared/MapCanvas.svelte';
	import type { MapLayers, RobotPose } from '#shared/drawMap.ts';
	import type { GardenMap } from '#features/maps/types.ts';
	import type { RobotStatus } from '#features/robot/types.ts';
	import { canStartRoute, formatDistance, formatDuration, planMatches } from './plan.ts';
	import type { Tool } from './selection.ts';
	import { PlanSession } from './session.svelte.ts';
	import type { Parameters, Plan, PreviewRequest } from './types.ts';

	let {
		map,
		robot = null,
		plan,
		planLoaded,
		defaults,
		mowSpeedMps,
		robotStatus,
		preview,
		discard,
		start
	}: {
		/** The active map; null = none. */
		map: GardenMap | null;
		robot?: RobotPose | null;
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
	} = $props();

	const session = new PlanSession();
	let busy = $state<'calculate' | 'start' | 'discard' | null>(null);
	let error = $state('');

	$effect(() => {
		if (planLoaded) session.adopt(plan);
	});
	$effect(() => {
		if (defaults) session.useDefaults(defaults);
	});

	const shownPlan = $derived(plan && map && plan.mapId === map.id ? plan : null);
	const outdated = $derived(
		shownPlan !== null && session.request !== null && !planMatches(shownPlan, session.request)
	);

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

	const tools: { tool: Tool; label: string }[] = [
		{ tool: 'all', label: 'Whole garden' },
		{ tool: 'rectangle', label: 'Rectangle' },
		{ tool: 'polygon', label: 'Polygon' }
	];

	const toolHint: Record<Tool, string> = {
		all: 'The route covers the whole garden.',
		rectangle: 'Drag on the map to draw a rectangle.',
		polygon: 'Tap the map to add corners, drag a corner to move it.'
	};

	async function run(what: NonNullable<typeof busy>, action: () => Promise<unknown>) {
		error = '';
		busy = what;
		try {
			await action();
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = null;
		}
	}

	const startable = $derived(shownPlan !== null && !outdated && canStartRoute(robotStatus));
</script>

<div class="planner">
	<div class="map">
		<MapCanvas
			{layers}
			label="Map for planning a route"
			interact={session.tool === 'all' ? undefined : interact}
		/>
	</div>
	<aside aria-label="Plan a route">
		{#if !map}
			<p class="empty">No active map. Choose or draw one under Maps.</p>
		{:else}
			<section>
				<h2>Area</h2>
				<div class="segmented" role="radiogroup" aria-label="Area">
					{#each tools as t (t.tool)}
						<label class:selected={session.tool === t.tool}>
							<input
								type="radio"
								name="tool"
								checked={session.tool === t.tool}
								onchange={() => session.setTool(t.tool)}
							/>
							{t.label}
						</label>
					{/each}
				</div>
				<p class="hint">{toolHint[session.tool]}</p>
				{#if session.tool !== 'all'}
					<!-- always there, so the form below does not jump when drawing starts -->
					<div class="row">
						{#if session.tool === 'polygon'}
							<button
								type="button"
								disabled={session.selection.length === 0}
								onclick={() => session.removeLastCorner()}
							>
								Remove last corner
							</button>
						{/if}
						<button
							type="button"
							disabled={session.selection.length === 0}
							onclick={() => session.clearSelection()}
						>
							Clear selection
						</button>
					</div>
				{/if}
			</section>

			{#if session.parameters}
				{@const p = session.parameters}
				<section>
					<h2>Pattern</h2>
					<div class="segmented" role="radiogroup" aria-label="Pattern">
						{#each ['lines', 'squares', 'rings'] as const as pattern (pattern)}
							<label class:selected={p.pattern === pattern}>
								<input type="radio" name="pattern" value={pattern} bind:group={p.pattern} />
								{pattern[0].toUpperCase() + pattern.slice(1)}
							</label>
						{/each}
					</div>
					<div class="grid">
						<label class="field">
							Lane width <span class="hint">m</span>
							<input type="number" step="0.01" bind:value={p.widthM} />
						</label>
						<label class="field">
							Angle <span class="hint">°</span>
							<input type="number" step="1" bind:value={p.angleDeg} />
						</label>
						<label class="field">
							Distance to border <span class="hint">lanes</span>
							<input type="number" step="1" bind:value={p.distanceToBorder} />
						</label>
						<label class="field">
							Border laps
							<input type="number" step="1" bind:value={p.borderLaps} />
						</label>
					</div>
					<label class="switch">
						Mow the area
						<input type="checkbox" bind:checked={p.mowArea} />
					</label>
					<label class="switch">
						Mow around exclusions
						<input type="checkbox" bind:checked={p.mowExclusions} />
					</label>
					<label class="switch">
						Border counter-clockwise
						<input type="checkbox" bind:checked={p.borderCcw} />
					</label>
				</section>
			{/if}

			<section>
				<button
					type="button"
					class:primary={!shownPlan || outdated}
					disabled={busy !== null || session.request === null}
					onclick={() => run('calculate', () => preview(session.request!))}
				>
					{busy === 'calculate' ? 'Calculating…' : 'Calculate route'}
				</button>
				{#if session.tool !== 'all' && session.request === null}
					<p class="hint">Select a part of the garden first.</p>
				{/if}
				{#if shownPlan}
					<div class="result" aria-label="Planned route">
						<strong>{formatDistance(shownPlan.distanceM)}</strong>
						<span>{shownPlan.route.length} points</span>
						{#if formatDuration(shownPlan.distanceM, mowSpeedMps)}
							<span>about {formatDuration(shownPlan.distanceM, mowSpeedMps)}</span>
						{/if}
					</div>
					{#if outdated}
						<p class="hint">
							Area or parameters changed since. Calculate again to update the route.
						</p>
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
	</aside>
</div>

<style>
	.planner {
		min-height: calc(100dvh - var(--nav-bottom));
		display: grid;
		gap: 16px;
		padding: 16px;
		grid-template-columns: 1fr;
		grid-template-rows: minmax(300px, 55dvh) auto;
	}
	.map {
		min-height: 0;
	}
	aside {
		display: flex;
		flex-direction: column;
		gap: 20px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 16px;
	}
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
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.grid {
		display: grid;
		gap: 12px;
		grid-template-columns: repeat(2, minmax(0, 1fr));
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
	@media (min-width: 900px) {
		.planner {
			height: 100dvh;
			grid-template-columns: 1fr 360px;
			grid-template-rows: 1fr;
		}
		aside {
			overflow-y: auto;
		}
	}
</style>
