<script lang="ts">
	// One value over time as a line, with its axis.
	import { linePath, niceScale, timeLabel } from './stats.ts';
	import type { Sample } from './types.ts';

	let {
		title,
		unit,
		samples,
		value,
		from,
		to,
		digits = 1
	}: {
		title: string;
		unit: string;
		samples: Sample[];
		value: (s: Sample) => number;
		from: Date;
		to: Date;
		digits?: number;
	} = $props();

	const height = 120;
	const axis = 40; // room for the labels on the left
	let width = $state(300);

	const scale = $derived(niceScale(samples.map(value)));
	const path = $derived(
		linePath(samples, value, {
			from: from.getTime(),
			to: to.getTime(),
			min: scale.min,
			max: scale.max,
			width: Math.max(width - axis, 10),
			height
		})
	);
	const y = (v: number) => height - ((v - scale.min) / (scale.max - scale.min || 1)) * height;
	const times = $derived(
		[0, 0.5, 1].map((f) => {
			const ms = to.getTime() - from.getTime();
			return timeLabel(new Date(from.getTime() + f * ms), ms);
		})
	);
	const last = $derived(samples.length ? value(samples[samples.length - 1]) : null);
</script>

<figure class="card">
	<figcaption>
		<span>{title}</span>
		{#if last !== null}<strong>{last.toFixed(digits)} {unit}</strong>{/if}
	</figcaption>
	<div class="plot" bind:clientWidth={width}>
		{#if samples.length === 0}
			<p class="empty">No data in this time span.</p>
		{:else}
			<svg viewBox="0 0 {width} {height + 8}" role="img" aria-label="{title} over time">
				{#each scale.ticks as t (t)}
					<line class="grid" x1={axis} x2={width} y1={y(t) + 4} y2={y(t) + 4} />
					<text x={axis - 6} y={y(t) + 8}>{Number(t.toFixed(3))}</text>
				{/each}
				<path d={path} transform="translate({axis} 4)" />
			</svg>
			<div class="times" style:padding-left="{axis}px" aria-hidden="true">
				{#each times as t, i (i)}<span>{t}</span>{/each}
			</div>
		{/if}
	</div>
</figure>

<style>
	figure {
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 8px;
	}
	figcaption {
		display: flex;
		justify-content: space-between;
		gap: 8px;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	figcaption strong {
		color: var(--text);
		font-variant-numeric: tabular-nums;
	}
	.plot {
		min-height: 128px;
	}
	svg {
		display: block;
		width: 100%;
		height: 128px;
		overflow: visible;
	}
	path {
		fill: none;
		stroke: var(--text);
		stroke-width: 1.5;
		stroke-linejoin: round;
	}
	.grid {
		stroke: var(--border);
		stroke-width: 1;
	}
	text {
		fill: var(--text-muted);
		font-size: 11px;
		text-anchor: end;
		font-variant-numeric: tabular-nums;
	}
	.times {
		display: flex;
		justify-content: space-between;
		margin-top: 4px;
		color: var(--text-muted);
		font-size: 11px;
	}
	.empty {
		margin: 0;
		padding: 40px 0;
		text-align: center;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
</style>
