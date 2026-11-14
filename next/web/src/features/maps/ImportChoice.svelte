<script lang="ts">
	// A Sunray export holds several maps: choose the one to open in the editor.
	import type { MapShape } from './types.ts';

	let {
		fileName,
		maps,
		onpick,
		ondismiss
	}: {
		fileName: string;
		maps: MapShape[];
		onpick: (map: MapShape) => void;
		ondismiss: () => void;
	} = $props();
</script>

<section class="choice" aria-label="Maps in {fileName}">
	<header>
		<h2>{maps.length} maps in {fileName}</h2>
		<button type="button" class="link" onclick={ondismiss}>Close</button>
	</header>
	<p class="hint">Open one in the editor, check it and save it. Then come back for the next.</p>
	<ul>
		{#each maps as m (m.name)}
			<li>
				<button type="button" onclick={() => onpick(m)}>
					<span class="name">{m.name}</span>
					<span class="hint">
						{m.perimeter.length} points · {m.exclusions.length} exclusion{m.exclusions.length === 1
							? ''
							: 's'}{m.dock.length > 0 ? ' · dock' : ''}
					</span>
				</button>
			</li>
		{/each}
	</ul>
</section>

<style>
	.choice {
		display: grid;
		gap: 8px;
		padding: 12px;
		border-radius: 12px;
		background: var(--surface-sunken);
	}
	header {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 8px;
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
		overflow-wrap: anywhere;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
	}
	li button {
		width: 100%;
		display: flex;
		justify-content: space-between;
		align-items: baseline;
		gap: 8px;
		text-align: left;
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
</style>
