<script lang="ts">
	// The robot's history: time shares, counters and charts for a time span.
	import { onMount } from 'svelte';
	import { fetchStats } from './api.ts';
	import Chart from './Chart.svelte';
	import { formatDistance, formatDuration, percent, ranges, shares, span } from './stats.ts';
	import type { RangeName, StatsResponse } from './types.ts';

	let {
		load = (from: Date, to: Date) => fetchStats(from, to, 300),
		now = () => new Date(),
		refreshMs = 60_000
	}: {
		load?: (from: Date, to: Date) => Promise<StatsResponse>;
		now?: () => Date;
		/** How often the shown span moves on and is loaded again; 0 = never. */
		refreshMs?: number;
	} = $props();

	let range = $state<RangeName>('day');
	let data = $state.raw<StatsResponse | null>(null);
	let shown = $state.raw<{ from: Date; to: Date } | null>(null);
	let error = $state('');
	let seq = 0;

	async function reload() {
		const s = span(range, now());
		const mine = ++seq;
		try {
			const d = await load(s.from, s.to);
			if (mine !== seq) return; // a newer request is under way
			data = d;
			shown = s;
			error = '';
		} catch (err) {
			if (mine === seq) error = err instanceof Error ? err.message : String(err);
		}
	}

	onMount(() => {
		if (refreshMs <= 0) return;
		const t = setInterval(reload, refreshMs);
		return () => clearInterval(t);
	});

	$effect(() => {
		void range; // reload whenever the span changes
		reload();
	});

	const time = $derived(
		data
			? shares(data.totals, [
					{ key: 'mowSec', label: 'Mowing' },
					{ key: 'chargeSec', label: 'Charging' },
					{ key: 'idleSec', label: 'Idle' }
				])
			: []
	);
	const gps = $derived(
		data
			? shares(data.totals, [
					{ key: 'mowFixSec', label: 'Fix' },
					{ key: 'mowFloatSec', label: 'Float' },
					{ key: 'mowInvalidSec', label: 'Invalid' }
				])
			: []
	);
	const counters: { key: string; label: string }[] = [
		{ key: 'obstacles', label: 'Obstacles' },
		{ key: 'bumper', label: 'Bumper' },
		{ key: 'sonar', label: 'Sonar' },
		{ key: 'lift', label: 'Lift' },
		{ key: 'tof', label: 'ToF' },
		{ key: 'rotationTimeouts', label: 'Rotation timeouts' },
		{ key: 'imuNoRotation', label: 'IMU no rotation' },
		{ key: 'diffImuWheelYawSpeed', label: 'IMU/wheel yaw speed' },
		{ key: 'gpsMotionTimeouts', label: 'GPS motion timeouts' },
		{ key: 'gpsNoSpeed', label: 'GPS no speed' },
		{ key: 'gpsJumps', label: 'GPS jumps' },
		{ key: 'floatRecoveries', label: 'Float recoveries' },
		{ key: 'invalidRecoveries', label: 'Invalid recoveries' },
		{ key: 'imuRecoveries', label: 'IMU recoveries' },
		{ key: 'gpsChecksumErrors', label: 'GPS checksum errors' },
		{ key: 'dgpsChecksumErrors', label: 'DGPS checksum errors' }
	];
</script>

<div class="segmented" role="radiogroup" aria-label="Time span">
	{#each ranges as r (r.name)}
		<label class:selected={range === r.name}>
			<input type="radio" name="range" value={r.name} bind:group={range} />
			{r.label}
		</label>
	{/each}
</div>

{#if error}
	<p class="error" role="alert">{error}</p>
{/if}

{#if data && shown}
	<div class="grid">
		{#snippet bar(title: string, parts: typeof time, note: string)}
			<section class="card">
				<h2>{title}</h2>
				{#if parts.every((p) => p.seconds === 0)}
					<p class="muted">Nothing recorded in this time span.</p>
				{:else}
					<div class="bar" aria-hidden="true">
						{#each parts as p (p.key)}
							<span class="part {p.key}" style:flex-grow={p.part}></span>
						{/each}
					</div>
					<dl class="legend">
						{#each parts as p (p.key)}
							<div>
								<dt><span class="dot {p.key}"></span>{p.label}</dt>
								<dd>{formatDuration(p.seconds)} · {percent(p.part)}</dd>
							</div>
						{/each}
					</dl>
				{/if}
				<p class="muted note">{note}</p>
			</section>
		{/snippet}
		{@render bar('Time', time, 'From the robot’s counters, in whole hours.')}
		{@render bar('GPS while mowing', gps, 'Mowing time by GPS solution.')}

		<section class="card">
			<h2>Mowing</h2>
			<dl class="numbers">
				<div>
					<dt>Distance mowed</dt>
					<dd>{formatDistance(data.totals.distanceMowM ?? 0)}</dd>
				</div>
				<div>
					<dt>Mow motor recovery</dt>
					<dd>{formatDuration(data.totals.mowMotorRecoverySec ?? 0)}</dd>
				</div>
				<div>
					<dt>Longest cycle</dt>
					<dd>{(data.totals.maxCycleTimeSec ?? 0).toFixed(2)} s</dd>
				</div>
				<div>
					<dt>Oldest correction data</dt>
					<dd>{(data.totals.maxDgpsAgeSec ?? 0).toFixed(1)} s</dd>
				</div>
			</dl>
		</section>
	</div>

	<h2 class="charts-title">History</h2>
	<div class="grid">
		<Chart
			title="Battery"
			unit="V"
			samples={data.samples}
			value={(s) => s.batteryV}
			{...shown}
			digits={2}
		/>
		<Chart
			title="Current"
			unit="A"
			samples={data.samples}
			value={(s) => s.amps}
			{...shown}
			digits={2}
		/>
		<Chart
			title="Satellites"
			unit=""
			samples={data.samples}
			value={(s) => s.satellites}
			{...shown}
			digits={0}
		/>
		<Chart
			title="GPS accuracy"
			unit="cm"
			samples={data.samples}
			value={(s) => s.accuracyM * 100}
			{...shown}
		/>
		<Chart
			title="Lateral error"
			unit="cm"
			samples={data.samples}
			value={(s) => s.lateralErrorM * 100}
			{...shown}
		/>
	</div>

	<div class="grid events">
		<section class="card">
			<h2>Events</h2>
			<dl class="numbers">
				{#each counters as c (c.key)}
					<div class:zero={!data.totals[c.key]}>
						<dt>{c.label}</dt>
						<dd>{data.totals[c.key] ?? 0}</dd>
					</div>
				{/each}
			</dl>
		</section>
	</div>
{:else if !error}
	<p class="muted">Loading statistics…</p>
{/if}

<style>
	.segmented {
		margin-bottom: 16px;
	}
	.grid {
		display: grid;
		gap: 16px;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
		align-items: start;
	}
	h2 {
		margin: 0 0 12px;
		font-size: 1rem;
	}
	.events {
		margin-top: 16px;
	}
	.charts-title {
		margin: 28px 0 12px;
		font-size: 1.2rem;
	}
	.bar {
		display: flex;
		height: 14px;
		border-radius: 7px;
		overflow: hidden;
		background: var(--tone-neutral);
		gap: 2px;
	}
	.part {
		flex-basis: 0;
		min-width: 0;
	}
	/* Gray steps; color only where it means something (invalid GPS). */
	.mowSec,
	.mowFixSec {
		background: var(--text);
	}
	.chargeSec,
	.mowFloatSec {
		background: var(--text-muted);
	}
	.idleSec {
		background: var(--border);
	}
	.mowInvalidSec {
		background: var(--danger);
	}
	.legend,
	.numbers {
		margin: 12px 0 0;
		display: grid;
		gap: 6px;
	}
	.legend div,
	.numbers div {
		display: flex;
		justify-content: space-between;
		gap: 12px;
	}
	dt {
		color: var(--text-muted);
		display: flex;
		align-items: center;
		gap: 8px;
	}
	dd {
		margin: 0;
		font-variant-numeric: tabular-nums;
	}
	.zero dd {
		color: var(--text-muted);
	}
	.dot {
		width: 10px;
		height: 10px;
		border-radius: 50%;
		display: inline-block;
	}
	.muted {
		margin: 0;
		color: var(--text-muted);
	}
	.note {
		margin-top: 10px;
		font-size: 0.8rem;
	}
	.error {
		color: var(--tone-danger-text);
	}
</style>
