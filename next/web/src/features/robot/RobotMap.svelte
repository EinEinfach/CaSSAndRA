<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import MapCanvas from '#shared/MapCanvas.svelte';
	import type { MapLayers } from '#shared/drawMap.ts';
	import type { Point } from '#shared/viewport.ts';
	import { animatesMotion, browserFrames, RobotMotion, type FrameClock } from './motion.svelte.ts';
	import type { RobotMap, RobotState } from './types.ts';

	let {
		state,
		map,
		trail,
		frames = browserFrames
	}: { state: RobotState | null; map: RobotMap; trail: Point[]; frames?: FrameClock } = $props();

	const motion = new RobotMotion(untrack(() => frames));
	onDestroy(() => motion.stop());

	$effect(() => {
		const target =
			state && state.status !== 'offline'
				? { position: state.position, headingRad: state.headingRad }
				: null;
		const animate = state ? animatesMotion(state.status) : false;
		untrack(() => motion.update(target, animate));
	});

	// The trail ends where the robot is drawn, not ahead of it at the reported position.
	const shownTrail = $derived.by(() => {
		const pose = motion.pose;
		const last = trail.at(-1);
		if (!pose || !last || !state) return trail;
		if (last.x !== state.position.x || last.y !== state.position.y) return trail;
		return [...trail.slice(0, -1), pose.position];
	});

	const layers: MapLayers = $derived({
		perimeter: map.perimeter,
		exclusions: map.exclusions,
		dock: map.dock,
		way: map.way,
		wayDoneIndex: state?.status === 'mow' ? state.mowPointIndex : 0,
		trail: shownTrail,
		target: state && ['mow', 'transit', 'docking'].includes(state.status) ? state.target : null,
		robot: motion.pose
	});
</script>

<MapCanvas {layers} label="Garden map with robot position" />
