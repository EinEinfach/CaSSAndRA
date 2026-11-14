<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchLogs, fetchSystem, sendCommand } from '#features/logs/api.ts';
	import CommandInput from '#features/logs/CommandInput.svelte';
	import { LogFeed } from '#features/logs/feed.svelte.ts';
	import LogView from '#features/logs/LogView.svelte';
	import SystemInfo from '#features/logs/SystemInfo.svelte';

	const feed = new LogFeed((after) => fetchLogs(after));

	onMount(() => {
		feed.start();
		return () => feed.stop();
	});
</script>

<svelte:head>
	<title>Log · CaSSAndRA</title>
</svelte:head>

<div class="page">
	<h1>Log</h1>
	<div class="grid">
		<LogView {feed} />
		<div class="side">
			<CommandInput send={(line) => sendCommand(line)} />
			<SystemInfo load={() => fetchSystem()} />
		</div>
	</div>
</div>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: 20px 16px;
	}
	h1 {
		margin: 0 0 16px;
		font-size: 1.6rem;
	}
	.grid {
		display: grid;
		gap: 16px;
	}
	.side {
		display: grid;
		gap: 16px;
		align-content: start;
	}
	/* The log gets the height of the screen, so the page itself does not scroll. */
	.grid > :global(.log) {
		height: min(70vh, 640px);
	}
	@media (min-width: 900px) {
		.grid {
			grid-template-columns: minmax(0, 1fr) 340px;
		}
		.grid > :global(.log) {
			height: calc(100vh - 110px);
		}
	}
</style>
