<script lang="ts">
	// The layout of every page around a map: the map on the left in the full
	// height, a panel of fixed width on the right; on phones the map on top.
	// The map keeps the same size and place on all pages, so switching pages
	// does not move it.
	import type { Snippet } from 'svelte';

	let {
		map,
		panel,
		label
	}: {
		map: Snippet;
		panel: Snippet;
		/** Name of the panel for assistive technology. */
		label: string;
	} = $props();
</script>

<div class="layout">
	<div class="map">{@render map()}</div>
	<aside aria-label={label}>{@render panel()}</aside>
</div>

<style>
	.layout {
		min-height: calc(100dvh - var(--nav-bottom));
		display: grid;
		gap: 16px;
		padding: 16px;
		grid-template-columns: minmax(0, 1fr);
		grid-template-rows: minmax(300px, 55dvh) auto;
	}
	.map {
		position: relative;
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
		min-width: 0;
	}
	@media (min-width: 900px) {
		.layout {
			height: 100dvh;
			grid-template-columns: minmax(0, 1fr) var(--panel-width);
			grid-template-rows: minmax(0, 1fr);
		}
		aside {
			align-self: start;
			max-height: 100%;
			overflow-y: auto;
		}
	}
</style>
