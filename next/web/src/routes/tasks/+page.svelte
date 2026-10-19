<script lang="ts">
	import { onMount } from 'svelte';
	import { MapsStore } from '#features/maps/store.svelte.ts';
	import { RobotStore } from '#features/robot/store.svelte.ts';
	import type { SettingsView } from '#features/settings/types.ts';
	import { clearPreview, previewRoute } from '#features/tasks/api.ts';
	import { PlanStore } from '#features/tasks/store.svelte.ts';
	import TaskPlanner from '#features/tasks/TaskPlanner.svelte';
	import type { Parameters } from '#features/tasks/types.ts';
	import { useStream } from '#shared/streamContext.ts';

	const stream = useStream();
	const maps = new MapsStore();
	const plans = new PlanStore();
	const robot = new RobotStore();
	let defaults = $state<Parameters | null>(null);
	let mowSpeedMps = $state(0);

	onMount(() => {
		const stops = [
			maps.connect(stream),
			plans.connect(stream),
			robot.connect(stream),
			stream.on<SettingsView>('settings', ({ settings }) => {
				defaults = settings.planner;
				mowSpeedMps = settings.rover.mowSpeedMps;
			})
		];
		return () => stops.forEach((stop) => stop());
	});

	const pose = $derived(
		robot.connected && robot.state && robot.state.status !== 'offline'
			? { position: robot.state.position, headingRad: robot.state.headingRad }
			: null
	);
</script>

<svelte:head>
	<title>Tasks · CaSSAndRA</title>
</svelte:head>

<TaskPlanner
	map={maps.active}
	robot={pose}
	plan={plans.plan}
	planLoaded={plans.loaded}
	{defaults}
	{mowSpeedMps}
	preview={(req) => previewRoute(req)}
	discard={() => clearPreview()}
/>
