<script lang="ts">
	import MapCanvas from '#shared/MapCanvas.svelte';
	import type { MapLayers } from '#shared/drawMap.ts';
	import type { Point } from '#shared/viewport.ts';
	import type { RobotMap, RobotState } from './types.ts';

	let { state, map, trail }: { state: RobotState | null; map: RobotMap; trail: Point[] } = $props();

	const layers: MapLayers = $derived({
		perimeter: map.perimeter,
		exclusions: map.exclusions,
		dock: map.dock,
		way: map.way,
		wayDoneIndex: state?.status === 'mow' ? state.mowPointIndex : 0,
		trail,
		target: state && ['mow', 'transit', 'docking'].includes(state.status) ? state.target : null,
		robot:
			state && state.status !== 'offline'
				? { position: state.position, headingRad: state.headingRad }
				: null
	});
</script>

<MapCanvas {layers} label="Garden map with robot position" />
