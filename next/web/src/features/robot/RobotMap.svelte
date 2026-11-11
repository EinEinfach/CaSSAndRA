<script lang="ts">
	import { onDestroy, untrack } from 'svelte';
	import MapCanvas, { type MapInteraction } from '#shared/MapCanvas.svelte';
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
		clearTrail,
		clearObstacles,
		interact,
		goal = null,
		planned = null,
		overlay = {}
	}: {
		state: RobotState | null;
		map: RobotMap;
		trail: Point[];
		frames?: FrameClock;
		/** Shows a button that starts a new trail. */
		clearTrail?: () => Promise<void>;
		/** Shows a button that forgets the obstacles while there are some. */
		clearObstacles?: () => Promise<void>;
		/** Pointer handling, e.g. while picking a goal; without it the map only pans. */
		interact?: MapInteraction;
		goal?: Point | null;
		/** A route not yet sent, drawn instead of the robot's way. */
		planned?: Point[] | null;
		/** A selection being drawn, e.g. the area to mow. */
		overlay?: Pick<MapLayers, 'selection' | 'edit'>;
	} = $props();

	let clearing = $state(false);
	async function clear(what: string, action?: () => Promise<void>) {
		clearing = true;
		try {
			await action?.();
		} catch (err) {
			console.error(`clearing the ${what} failed`, err);
		} finally {
			clearing = false;
		}
	}

	const obstacles = $derived(robot?.obstacles ?? []);

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
		way: planned ?? map.way,
		wayDoneIndex: !planned && robot?.status === 'mow' ? robot.mowPointIndex : 0,
		trail: shownTrail,
		obstacles,
		target: robot && ['mow', 'transit', 'docking'].includes(robot.status) ? robot.target : null,
		goal,
		robot: motion.pose,
		...overlay
	});
</script>

<div class="robot-map">
	<MapCanvas {layers} {interact} label="Garden map with robot position" />
	<div class="tools">
		{#if clearTrail && trail.length > 1}
			<button
				type="button"
				onclick={() => clear('trail', clearTrail)}
				disabled={clearing}
				title="Remove the driven path; it also starts anew when the robot docks"
			>
				Clear trail
			</button>
		{/if}
		{#if clearObstacles && obstacles.length > 0}
			<button
				type="button"
				onclick={() => clear('obstacles', clearObstacles)}
				disabled={clearing}
				title="Forget the obstacles until the robot reports them again"
			>
				Clear obstacles
			</button>
		{/if}
	</div>
</div>

<style>
	.robot-map {
		position: relative;
		height: 100%;
	}
	.tools {
		position: absolute;
		top: 8px;
		left: 8px;
		display: flex;
		gap: 8px;
	}
</style>
