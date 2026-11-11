<script lang="ts">
	// Choosing the area of the current part: whole garden, rectangle or polygon.
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

<style>
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
</style>
