<script lang="ts">
	import { onMount } from 'svelte';
	import { MapsStore } from '#features/maps/store.svelte.ts';
	import Controls from '#features/robot/Controls.svelte';
	import { canDriveManually } from '#features/robot/drive.ts';
	import Joystick from '#features/robot/Joystick.svelte';
	import Progress from '#features/robot/Progress.svelte';
	import { clearObstacles, command, skipToProgress } from '#features/robot/api.ts';
	import RemoteControl from '#features/robot/RemoteControl.svelte';
	import RobotMap from '#features/robot/RobotMap.svelte';
	import StatusPanel from '#features/robot/StatusPanel.svelte';
	import { RobotStore } from '#features/robot/store.svelte.ts';
	import type { SettingsView } from '#features/settings/types.ts';
	import { clearPreview, gotoPoint, previewRoute, startMowing } from '#features/tasks/api.ts';
	import GotoControl from '#features/tasks/GotoControl.svelte';
	import { GotoPicker } from '#features/tasks/goto.svelte.ts';
	import { LivePlan } from '#features/tasks/livePlan.svelte.ts';
	import MowPlanner from '#features/tasks/MowPlanner.svelte';
	import { PlanStore, TaskStore } from '#features/tasks/store.svelte.ts';
	import MapLayout from '#shared/MapLayout.svelte';
	import { useStream } from '#shared/streamContext.ts';

	const stream = useStream();
	const robot = new RobotStore();
	const maps = new MapsStore();
	const picker = new GotoPicker();
	const plans = new PlanStore();
	const tasks = new TaskStore();
	const live = new LivePlan();
	let mowSpeedMps = $state(0);

	onMount(() => {
		const stops = [
			robot.connect(stream),
			maps.connect(stream),
			plans.connect(stream),
			tasks.connect(stream),
			stream.on<SettingsView>('settings', ({ settings }) => {
				live.session.useDefaults(settings.planner);
				mowSpeedMps = settings.rover.mowSpeedMps;
			})
		];
		return () => stops.forEach((stop) => stop());
	});

	$effect(() => {
		if (plans.loaded) live.adopt(plans.plan);
	});
	const mapTasks = $derived(tasks.forMap(maps.active?.id));
	$effect(() => {
		const ids = mapTasks.map((t) => t.id);
		live.session.keepChosen(ids);
	});
	// A plan of another (older) active map cannot be started.
	const plan = $derived(
		plans.plan && maps.active && plans.plan.mapId === maps.active.id ? plans.plan : null
	);

	const status = $derived(robot.connected && robot.state ? robot.state.status : 'offline');
	// What the robot has wins; before it reports a map, show the active one.
	// Picking a goal or planning a route shows the active map: the way is planned on it.
	const planning = $derived(picker.picking || live.open);
	const shownMap = $derived(
		(robot.map.perimeter.length > 0 && !planning) || !maps.active
			? robot.map
			: {
					perimeter: maps.active.perimeter,
					exclusions: maps.active.exclusions,
					dock: maps.active.dock,
					way: []
				}
	);
</script>

<MapLayout label="Robot">
	{#snippet map()}
		<RobotMap
			state={robot.state}
			map={shownMap}
			trail={robot.trail}
			clearTrail={() => robot.clearTrail()}
			clearObstacles={() => clearObstacles()}
			interact={picker.picking ? picker.interact : live.drawing ? live.interact : undefined}
			goal={picker.goal}
			planned={live.open ? (plan?.route ?? null) : null}
			overlay={live.drawing ? live.session.canvasLayers : {}}
		/>
		<div class="controls">
			<Controls {status} />
		</div>
	{/snippet}
	{#snippet panel()}
		<StatusPanel state={robot.state} connected={robot.connected} />
		{#if !live.open}
			<GotoControl {picker} {status} send={(goal) => gotoPoint(goal)} />
		{/if}
		{#if !picker.picking}
			<MowPlanner
				{live}
				{plan}
				tasks={mapTasks}
				{mowSpeedMps}
				{status}
				hasMap={maps.active !== null}
				preview={(req) => previewRoute(req)}
				start={() => startMowing()}
				discard={() => clearPreview()}
			/>
		{/if}
		<Progress
			{status}
			mowPointIndex={robot.state?.mowPointIndex ?? 0}
			routeLength={robot.map.way.length}
			skipNext={() => command('skip-next-point')}
			skipTo={(f) => skipToProgress(f)}
		/>
		<RemoteControl
			{status}
			mowMotorOn={robot.state?.mowMotorOn ?? false}
			speedMps={robot.state?.speedMps ?? 0}
		/>
		<div class="joystick">
			<Joystick disabled={!canDriveManually(status)} />
		</div>
	{/snippet}
</MapLayout>

<style>
	/* Over the map, bottom right, above the canvas. */
	.controls {
		position: absolute;
		right: 12px;
		bottom: 12px;
		z-index: 1;
	}
	.joystick {
		display: flex;
		justify-content: center;
	}
</style>
