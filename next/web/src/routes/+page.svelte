<script lang="ts">
	import { onMount } from 'svelte';
	import Controls from '#features/robot/Controls.svelte';
	import Joystick from '#features/robot/Joystick.svelte';
	import RobotMap from '#features/robot/RobotMap.svelte';
	import StatusPanel from '#features/robot/StatusPanel.svelte';
	import { RobotStore } from '#features/robot/store.svelte.ts';
	import { fetchHealth } from '#shared/api.ts';
	import { EventStream } from '#shared/events.ts';

	const robot = new RobotStore();
	let version = $state('');

	onMount(() => {
		const stream = new EventStream();
		const stop = robot.connect(stream);
		fetchHealth()
			.then((h) => (version = h.version))
			.catch(() => {});
		return () => {
			stop();
			stream.close();
		};
	});

	const status = $derived(robot.connected && robot.state ? robot.state.status : 'offline');
</script>

<div class="page">
	<header>
		<h1>CaSSAndRA</h1>
		<span class="version">{version}</span>
	</header>
	<main>
		<div class="map">
			<RobotMap state={robot.state} map={robot.map} trail={robot.trail} />
		</div>
		<aside>
			<StatusPanel state={robot.state} connected={robot.connected} />
			<Controls {status} />
			<div class="joystick">
				<Joystick disabled={!['idle', 'move'].includes(status)} />
			</div>
		</aside>
	</main>
</div>

<style>
	.page {
		min-height: 100dvh;
		display: flex;
		flex-direction: column;
		padding: 12px 16px 16px;
		gap: 12px;
	}
	header {
		display: flex;
		align-items: baseline;
		gap: 12px;
	}
	h1 {
		font-size: 1.25rem;
		margin: 0;
	}
	.version {
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	main {
		flex: 1;
		display: grid;
		gap: 16px;
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
		border-radius: 12px;
		padding: 16px;
	}
	.joystick {
		display: flex;
		justify-content: center;
	}
	@media (min-width: 900px) {
		main {
			grid-template-columns: 1fr 340px;
			grid-template-rows: 1fr;
		}
		aside {
			align-self: start;
		}
	}
</style>
