<script lang="ts">
	import AreaTools from './AreaTools.svelte';
	import ParametersForm from './ParametersForm.svelte';
	import type { PlanSession } from './session.svelte.ts';

	let { session }: { session: PlanSession } = $props();
</script>

{#if session.part}
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
		<AreaTools {session} />
	</section>

	<section>
		<h3>Pattern</h3>
		<ParametersForm parameters={session.part.parameters} />
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
</style>
