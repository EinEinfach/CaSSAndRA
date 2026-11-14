<script lang="ts">
	// Load of the computer CaSSAndRA runs on (legacy "server" info).
	import { onMount } from 'svelte';
	import type { SystemInfo } from './types.ts';

	let { load, refreshMs = 5000 }: { load: () => Promise<SystemInfo>; refreshMs?: number } =
		$props();

	let info = $state<SystemInfo | null>(null);
	let error = $state('');

	async function reload() {
		try {
			info = await load();
			error = '';
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		}
	}

	onMount(() => {
		void reload();
		if (refreshMs <= 0) return;
		const t = setInterval(reload, refreshMs);
		return () => clearInterval(t);
	});

	const fmt = (v: number | null | undefined, unit: string) =>
		v === null || v === undefined ? '–' : `${v.toFixed(1)} ${unit}`;

	const rows = $derived([
		{ label: 'CPU load', value: fmt(info?.cpuLoadPercent, '%') },
		{ label: 'CPU temperature', value: fmt(info?.cpuTempC, '°C') },
		{ label: 'Memory used', value: fmt(info?.memUsedPercent, '%') },
		{ label: 'Disk used', value: fmt(info?.diskUsedPercent, '%') }
	]);
</script>

<section class="card" aria-labelledby="system-title">
	<h2 id="system-title">Computer</h2>
	<dl>
		{#each rows as r (r.label)}
			<div>
				<dt>{r.label}</dt>
				<dd>{r.value}</dd>
			</div>
		{/each}
	</dl>
	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
</section>

<style>
	section {
		display: grid;
		gap: 10px;
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
	}
	dl {
		margin: 0;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 10px;
	}
	dt {
		color: var(--text-muted);
		font-size: 0.8rem;
	}
	dd {
		margin: 0;
		font-weight: 600;
		font-variant-numeric: tabular-nums;
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
