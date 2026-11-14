<!-- Test helper: a MapCanvas below a provided theme. -->
<script lang="ts">
	import MapCanvas from '#shared/MapCanvas.svelte';
	import type { MapLayers } from '#shared/drawMap.ts';
	import { provideTheme, type Theme } from '#shared/theme.svelte.ts';

	let { theme, layers }: { theme: Theme; layers: MapLayers } = $props();
	// svelte-ignore state_referenced_locally
	provideTheme(theme);
</script>

<MapCanvas {layers} />
