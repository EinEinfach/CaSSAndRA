<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import MapCanvas from '#shared/MapCanvas.svelte';
	import type { MapLayers } from '#shared/drawMap.ts';
	import type { Point } from '#shared/viewport.ts';
	import { animatesMotion, browserFrames, RobotMotion, type FrameClock } from './motion.svelte.ts';
	import type { RobotMap, RobotState } from './types.ts';

	// Renamed: a variable called "state" would turn $state(...) into a store subscription.
	let {
		state: robot,
		map,
		trail,
		frames = browserFrames,
		clearTrail
	}: {
		state: RobotState | null;
		map: RobotMap;
		trail: Point[];
		frames?: FrameClock;
		/** Shows a button that starts a new trail. */
		clearTrail?: () => Promise<void>;
	} = $props();

	let clearing = $state(false);
	async function clear() {
		clearing = true;
		try {
			await clearTrail?.();
		} catch (err) {
			console.error('clearing the trail failed', err);
		} finally {
			clearing = false;
		}
	}

	const motion = new RobotMotion(untrack(() => frames));
	onDestroy(() => motion.stop());

	$effect(() => {
		const target =
			robot && robot.status !== 'offline'
				? { position: robot.position, headingRad: robot.headingRad }
				: null;
		const animate = robot ? animatesMotion(robot.status) : false;
		untrack(() => motion.update(target, animate));
	});

	// The trail ends where the robot is drawn, not ahead of it at the reported position.
	const shownTrail = $derived.by(() => {
		const pose = motion.pose;
		const last = trail.at(-1);
		if (!pose || !last || !robot) return trail;
		if (last.x !== robot.position.x || last.y !== robot.position.y) return trail;
		return [...trail.slice(0, -1), pose.position];
	});

	const layers: MapLayers = $derived({
		perimeter: map.perimeter,
		exclusions: map.exclusions,
		dock: map.dock,
		way: map.way,
		wayDoneIndex: robot?.status === 'mow' ? robot.mowPointIndex : 0,
		trail: shownTrail,
		target: robot && ['mow', 'transit', 'docking'].includes(robot.status) ? robot.target : null,
		robot: motion.pose
	});
</script>

<div class="robot-map">
	<MapCanvas {layers} label="Garden map with robot position" />
	{#if clearTrail && trail.length > 1}
		<button
			type="button"
			class="clear"
			onclick={clear}
			disabled={clearing}
			title="Remove the driven path; it also starts anew when the robot docks"
		>
			Clear trail
		</button>
	{/if}
</div>

<style>
	.robot-map {
		position: relative;
		height: 100%;
	}
	.clear {
		position: absolute;
		top: 8px;
		left: 8px;
	}
</style>
