<!-- Test helper: a MapCanvas below a provided robot picture source. -->
<script lang="ts">
	import MapCanvas from '#shared/MapCanvas.svelte';
	import type { MapLayers } from '#shared/drawMap.ts';
	import { provideRobotPicture, type RobotPictureSource } from '#shared/robotPicture.svelte.ts';

	let { source, layers }: { source: RobotPictureSource; layers: MapLayers } = $props();
	// svelte-ignore state_referenced_locally
	provideRobotPicture(source);
</script>

<MapCanvas {layers} />
