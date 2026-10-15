<script lang="ts">
	import { untrack } from 'svelte';
	import MapCanvas, { type MapInteraction } from '#shared/MapCanvas.svelte';
	import type { Point } from '#shared/viewport.ts';
	import { allLayers, layerName, pointsOf } from './editor.ts';
	import { EditorSession } from './session.svelte.ts';
	import type { MapShape } from './types.ts';

	let {
		initial,
		title = 'New map',
		robotPosition = null,
		save,
		cancel
	}: {
		initial: MapShape;
		title?: string;
		robotPosition?: Point | null;
		save: (m: MapShape) => Promise<void>;
		cancel: () => void;
	} = $props();

	const session = new EditorSession(untrack(() => initial));
	let saving = $state(false);
	let error = $state('');

	const interact: MapInteraction = {
		tap: (p, mpp) => session.tap(p, mpp),
		press: (p, mpp) => session.press(p, mpp),
		move: (p) => session.move(p),
		release: () => session.release()
	};

	const layers = $derived({
		...session.canvasLayers,
		robot: robotPosition ? { position: robotPosition, headingRad: Math.PI / 2 } : null
	});

	async function submit() {
		error = '';
		saving = true;
		try {
			await save(session.result);
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			saving = false;
		}
	}

	function onKey(e: KeyboardEvent) {
		if (e.target instanceof HTMLInputElement) return;
		const mod = e.metaKey || e.ctrlKey;
		if (mod && e.key.toLowerCase() === 'z') {
			e.preventDefault();
			if (e.shiftKey) session.redo();
			else session.undo();
		} else if (e.key === 'Delete' || e.key === 'Backspace') {
			e.preventDefault();
			session.deleteSelected();
		}
	}
</script>

<svelte:window onkeydown={onKey} />

<section class="editor" aria-label="Map editor">
	<header>
		<input
			class="text name"
			aria-label="Map name"
			placeholder="Name of the map"
			bind:value={session.name}
		/>
		<div class="buttons">
			<button type="button" onclick={cancel} disabled={saving}>Cancel</button>
			<button
				type="button"
				class="primary"
				onclick={submit}
				disabled={saving || session.problems.length > 0}
			>
				{saving ? 'Saving…' : 'Save map'}
			</button>
		</div>
	</header>
	<p class="title">{title}</p>

	<div class="chips" role="tablist" aria-label="Part of the map">
		{#each allLayers(session.draft) as l (layerName(l))}
			<button
				type="button"
				role="tab"
				class="chip {l.kind}"
				aria-selected={session.isLayer(l)}
				onclick={() => session.selectLayer(l)}
			>
				{layerName(l)}
				<span class="count">{pointsOf(session.draft, l).length}</span>
			</button>
		{/each}
		<button type="button" class="chip add" onclick={() => session.newExclusion()}
			>+ Exclusion</button
		>
	</div>

	<div class="stage">
		<MapCanvas {layers} label="Map editor canvas" fitMode="once" {interact} />
		<div class="tools" role="toolbar" aria-label="Edit tools">
			<button
				type="button"
				onclick={() => session.undo()}
				disabled={!session.canUndo}
				title="Undo (Ctrl+Z)">Undo</button
			>
			<button
				type="button"
				onclick={() => session.redo()}
				disabled={!session.canRedo}
				title="Redo (Ctrl+Shift+Z)">Redo</button
			>
			<button
				type="button"
				onclick={() => session.deleteSelected()}
				disabled={session.selected === null}
				title="Delete point (Del)">Delete point</button
			>
			<button
				type="button"
				onclick={() => robotPosition && session.add(robotPosition)}
				disabled={!robotPosition}
				title="Add a point where the robot is">Robot position</button
			>
			<button
				type="button"
				onclick={() => session.clear()}
				disabled={pointsOf(session.draft, session.layer).length === 0 &&
					session.layer.kind !== 'exclusion'}
			>
				{session.layer.kind === 'exclusion' ? 'Remove exclusion' : 'Clear'}
			</button>
		</div>
	</div>

	<p class="help">
		Tap to add a point to the {layerName(session.layer).toLowerCase()}, tap a point to select it,
		drag it to move it. Polygons get new corners on their nearest edge.
	</p>
	{#if session.problems.length > 0}
		<ul class="problems" aria-label="Before saving">
			{#each session.problems as p (p)}<li>{p}</li>{/each}
		</ul>
	{/if}
	{#if error}<p class="error" role="alert">{error}</p>{/if}
</section>

<style>
	.editor {
		display: grid;
		gap: 10px;
		grid-template-rows: auto auto auto minmax(280px, 1fr);
		grid-auto-rows: auto;
		height: 100%;
	}
	header {
		display: flex;
		flex-wrap: wrap;
		gap: 10px;
		align-items: center;
	}
	.name {
		flex: 1 1 220px;
		font-size: 1.2rem;
		font-weight: 600;
	}
	.buttons {
		display: flex;
		gap: 8px;
	}
	.title {
		margin: -6px 0 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.chips {
		display: flex;
		gap: 6px;
		overflow-x: auto;
		padding-bottom: 2px;
	}
	.chip {
		flex: none;
		display: flex;
		align-items: center;
		gap: 6px;
		padding: 6px 12px;
		border-radius: 999px;
		font-size: 0.9rem;
	}
	.chip[aria-selected='true'] {
		background: var(--text);
		color: var(--bg);
		border-color: var(--text);
	}
	.chip::before {
		content: '';
		width: 10px;
		height: 10px;
		border-radius: 3px;
		background: var(--map-lawn);
		border: 1px solid var(--map-border);
	}
	.chip.exclusion::before {
		background: var(--map-exclusion);
		border-color: transparent;
	}
	.chip.dock::before {
		background: var(--map-dock);
		border-color: transparent;
	}
	.chip.searchWire::before {
		background: var(--map-wire);
		border-color: transparent;
	}
	.chip.add::before {
		display: none;
	}
	.count {
		font-size: 0.75rem;
		opacity: 0.7;
	}
	.stage {
		position: relative;
		min-height: 280px;
	}
	.tools {
		position: absolute;
		left: 50%;
		bottom: 12px;
		transform: translateX(-50%);
		display: flex;
		gap: 4px;
		padding: 4px;
		max-width: calc(100% - 24px);
		overflow-x: auto;
		border-radius: 14px;
		background: var(--surface);
		box-shadow: var(--shadow);
		border: 1px solid var(--border);
	}
	.tools button {
		flex: none;
		border: none;
		background: transparent;
		padding: 8px 10px;
		font-size: 0.85rem;
	}
	.tools button:not(:disabled):hover {
		background: var(--surface-sunken);
	}
	.help {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.problems {
		margin: 0;
		padding-left: 20px;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
