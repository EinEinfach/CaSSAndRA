<script lang="ts">
	// How a part is mowed; edits the given parameters in place.
	import type { Parameters } from './types.ts';

	let { parameters: p }: { parameters: Parameters } = $props();
</script>

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

<style>
	.hint {
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.grid {
		display: grid;
		gap: 12px;
		grid-template-columns: repeat(2, minmax(0, 1fr));
	}
</style>
