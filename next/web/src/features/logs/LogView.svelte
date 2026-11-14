<script lang="ts">
	// The app's log, newest at the bottom; follows new lines unless scrolled up.
	import { tick } from 'svelte';
	import { filterEntries, formatTime, type LogFeed } from './feed.svelte.ts';
	import type { Level } from './types.ts';

	let { feed }: { feed: LogFeed } = $props();

	let query = $state('');
	let minLevel = $state<Level>('DEBUG');
	let box = $state<HTMLElement>();
	let follow = true;

	const shown = $derived(filterEntries(feed.entries, query, minLevel));

	function onscroll() {
		if (!box) return;
		follow = box.scrollHeight - box.scrollTop - box.clientHeight < 24;
	}

	$effect(() => {
		void shown.length;
		if (!follow) return;
		void tick().then(() => {
			if (box) box.scrollTop = box.scrollHeight;
		});
	});
</script>

<section class="card log" aria-label="App log">
	<div class="tools">
		<input
			class="text"
			type="search"
			placeholder="Filter"
			aria-label="Filter log"
			bind:value={query}
		/>
		<select class="text" aria-label="Lowest level" bind:value={minLevel}>
			<option value="DEBUG">All levels</option>
			<option value="INFO">Info and above</option>
			<option value="WARN">Warnings and errors</option>
			<option value="ERROR">Errors</option>
		</select>
		<button type="button" aria-pressed={feed.paused} onclick={() => feed.togglePause()}>
			{feed.paused ? 'Resume' : 'Pause'}
		</button>
		<button type="button" onclick={() => feed.clear()}>Clear</button>
	</div>
	{#if feed.error}
		<p class="error" role="alert">Cannot load the log: {feed.error}</p>
	{/if}
	<div class="lines" bind:this={box} {onscroll} role="log" aria-label="Log lines">
		{#each shown as e (e.seq)}
			<div class="line" data-level={e.level}>
				<time datetime={e.time}>{formatTime(e.time)}</time>
				<span class="level">{e.level}</span>
				<span class="msg">{e.message}</span>
			</div>
		{:else}
			<p class="empty">{feed.entries.length === 0 ? 'No log lines yet.' : 'No line matches.'}</p>
		{/each}
	</div>
</section>

<style>
	.log {
		display: flex;
		flex-direction: column;
		gap: 10px;
		min-height: 0;
	}
	.tools {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.tools input {
		flex: 1 1 160px;
	}
	.tools select {
		flex: 0 1 auto;
		width: auto;
	}
	.lines {
		flex: 1;
		min-height: 240px;
		overflow: auto;
		background: var(--surface-sunken);
		border-radius: 10px;
		padding: 8px 10px;
		font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
		font-size: 0.78rem;
		line-height: 1.45;
	}
	.line {
		display: grid;
		grid-template-columns: auto 3.6em 1fr;
		gap: 8px;
	}
	time,
	.level {
		color: var(--text-muted);
	}
	.msg {
		overflow-wrap: anywhere;
		white-space: pre-wrap;
	}
	/* Phones: time and level above the message, which gets the full width. */
	@media (max-width: 600px) {
		.line {
			grid-template-columns: auto 1fr;
			gap: 0 8px;
			margin-bottom: 4px;
		}
		.msg {
			grid-column: 1 / -1;
		}
	}
	.line[data-level='WARN'] .level {
		color: var(--text);
		font-weight: 600;
	}
	.line[data-level='ERROR'] .level,
	.line[data-level='ERROR'] .msg {
		color: var(--tone-danger-text);
	}
	.empty {
		margin: 0;
		color: var(--text-muted);
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
