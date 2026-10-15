<script lang="ts">
	import { onMount } from 'svelte';
	import { MapsStore } from '#features/maps/store.svelte.ts';
	import Controls from '#features/robot/Controls.svelte';
	import Joystick from '#features/robot/Joystick.svelte';
	import RobotMap from '#features/robot/RobotMap.svelte';
	import StatusPanel from '#features/robot/StatusPanel.svelte';
	import { RobotStore } from '#features/robot/store.svelte.ts';
	import { useStream } from '#shared/streamContext.ts';

	const stream = useStream();
	const robot = new RobotStore();
	const maps = new MapsStore();

	onMount(() => {
		const stops = [robot.connect(stream), maps.connect(stream)];
		return () => stops.forEach((stop) => stop());
	});

	const status = $derived(robot.connected && robot.state ? robot.state.status : 'offline');
	// What the robot has wins; before it reports a map, show the active one.
	const shownMap = $derived(
		robot.map.perimeter.length > 0 || !maps.active
			? robot.map
			: {
					perimeter: maps.active.perimeter,
					exclusions: maps.active.exclusions,
					dock: maps.active.dock,
					way: []
				}
	);
</script>

<div class="page">
	<div class="map">
		<RobotMap state={robot.state} map={shownMap} trail={robot.trail} />
	</div>
	<aside>
		<StatusPanel state={robot.state} connected={robot.connected} />
		<Controls {status} />
		<div class="joystick">
			<Joystick disabled={!['idle', 'move'].includes(status)} />
		</div>
	</aside>
</div>

<style>
	.page {
		min-height: calc(100dvh - var(--nav-bottom));
		display: grid;
		gap: 16px;
		padding: 16px;
		grid-template-columns: 1fr;
		grid-template-rows: minmax(300px, 55dvh) auto;
	}
	.map {
		min-height: 0;
	}
	aside {
		display: flex;
		flex-direction: column;
		gap: 16px;
		background: var(--surface);
		border: 1px solid var(--border);
		border-radius: 16px;
		padding: 16px;
	}
	.joystick {
		display: flex;
		justify-content: center;
	}
	@media (min-width: 900px) {
		.page {
			height: 100dvh;
			grid-template-columns: 1fr 340px;
			grid-template-rows: 1fr;
		}
		aside {
			align-self: start;
		}
	}
</style>
