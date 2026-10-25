<script lang="ts">
	import { onMount } from 'svelte';
	import { MapsStore } from '#features/maps/store.svelte.ts';
	import { saveSchedule } from '#features/schedule/api.ts';
	import ScheduleEditor from '#features/schedule/ScheduleEditor.svelte';
	import { ScheduleStore } from '#features/schedule/store.svelte.ts';
	import { TaskStore } from '#features/tasks/store.svelte.ts';
	import { useStream } from '#shared/streamContext.ts';

	const stream = useStream();
	const schedule = new ScheduleStore();
	const tasks = new TaskStore();
	const maps = new MapsStore();
	let now = $state(new Date());

	onMount(() => {
		const stops = [schedule.connect(stream), tasks.connect(stream), maps.connect(stream)];
		const tick = setInterval(() => (now = new Date()), 30_000);
		return () => {
			stops.forEach((stop) => stop());
			clearInterval(tick);
		};
	});
</script>

<svelte:head>
	<title>Schedule · CaSSAndRA</title>
</svelte:head>

<div class="page">
	<h1>Schedule</h1>
	<ScheduleEditor
		view={schedule.view}
		tasks={tasks.tasks}
		maps={maps.maps}
		activeMapId={maps.active?.id}
		save={(s) => saveSchedule(s)}
		{now}
	/>
</div>

<style>
	.page {
		max-width: 760px;
		margin: 0 auto;
		padding: 20px 16px;
	}
	h1 {
		margin: 0 0 16px;
		font-size: 1.6rem;
	}
</style>
