<script lang="ts">
	import type { Tool } from './selection.ts';
	import type { PlanSession } from './session.svelte.ts';

	let { session }: { session: PlanSession } = $props();

	const tools: { tool: Tool; label: string }[] = [
		{ tool: 'all', label: 'Whole garden' },
		{ tool: 'rectangle', label: 'Rectangle' },
		{ tool: 'polygon', label: 'Polygon' }
	];

	const toolHint: Record<Tool, string> = {
		all: 'This part covers the whole garden.',
		rectangle: 'Drag on the map to draw a rectangle.',
		polygon: 'Tap the map to add corners, drag a corner to move it.'
	};
</script>

{#if session.part}
	{@const p = session.part.parameters}
	<div class="parts" role="tablist" aria-label="Parts">
		{#each session.parts.keys() as i (i)}
			<button
				type="button"
				role="tab"
				aria-selected={i === session.current}
				class:selected={i === session.current}
				onclick={() => session.selectPart(i)}
			>
				Part {i + 1}
			</button>
		{/each}
		<button type="button" class="add" onclick={() => session.addPart()}>+ Part</button>
	</div>
	{#if session.parts.length > 1}
		<p class="hint">
			Parts are mowed one after another, each from where the previous one ended.
			<button type="button" class="link" onclick={() => session.removePart()}>
				Remove part {session.current + 1}
			</button>
		</p>
	{/if}

	<section>
		<h3>Area</h3>
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

	<section>
		<h3>Pattern</h3>
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

<style>
	section {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	h3 {
		margin: 0;
		font-size: 0.9rem;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.parts {
		display: flex;
		flex-wrap: wrap;
		gap: 6px;
	}
	.parts button {
		padding: 6px 12px;
	}
	.parts button.selected {
		background: var(--tone-active);
		border-color: var(--text);
	}
	.parts .add {
		border-style: dashed;
	}
	.link {
		border: none;
		background: none;
		padding: 0;
		color: var(--text);
		text-decoration: underline;
		font-size: inherit;
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
</style>
