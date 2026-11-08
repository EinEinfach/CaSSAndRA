<script lang="ts">
	import {
		batteryLabel,
		dockReasonLabel,
		formatAmps,
		formatMeters,
		formatPoint,
		gpsLabel,
		satellitesLabel,
		statusLabel,
		statusTone
	} from './format.ts';
	import type { RobotState } from './types.ts';

	let { state, connected }: { state: RobotState | null; connected: boolean } = $props();

	const status = $derived(connected && state ? state.status : 'offline');
</script>

<section class="panel" aria-label="Robot status">
	<div class="headline">
		<span class="badge tone-{statusTone(status)}" data-testid="robot-status"
			>{statusLabel(status)}</span
		>
		{#if state?.dockReason}
			<span class="reason">{dockReasonLabel(state.dockReason)}</span>
		{/if}
	</div>
	{#if !connected}
		<p class="hint" role="status">No connection to CaSSAndRA – reconnecting…</p>
	{:else if state}
		<dl>
			<div>
				<dt>Battery</dt>
				<dd data-testid="robot-battery">{batteryLabel(state.socPercent, state.batteryV)}</dd>
			</div>
			<div>
				<dt>Current</dt>
				<dd>{formatAmps(state.amps)}</dd>
			</div>
			<div>
				<dt>GPS</dt>
				<dd>{gpsLabel(state.solution, state.accuracyM, state.satellites)}</dd>
			</div>
			<div>
				<dt>DGPS satellites · age</dt>
				<dd>{satellitesLabel(state.satellitesDgps, state.satellites, state.dgpsAgeSec)}</dd>
			</div>
			{#if state.sensor !== 'none'}
				<div>
					<dt>Sensor</dt>
					<dd class="warn">{state.sensor}</dd>
				</div>
			{/if}
		</dl>
		<details>
			<summary>Details</summary>
			<dl>
				<div>
					<dt>Position</dt>
					<dd>{formatPoint(state.position)}</dd>
				</div>
				<div>
					<dt>Target</dt>
					<dd>{formatPoint(state.target)}</dd>
				</div>
				<div>
					<dt>Mow point</dt>
					<dd>{state.mowPointIndex}</dd>
				</div>
				<div>
					<dt>Off the line</dt>
					<dd>{formatMeters(state.lateralErrorM)}</dd>
				</div>
				<div>
					<dt>Firmware</dt>
					<dd>{state.firmware} {state.firmwareVersion}</dd>
				</div>
			</dl>
		</details>
	{/if}
</section>

<style>
	.panel {
		display: grid;
		gap: 8px;
	}
	.headline {
		display: flex;
		align-items: center;
		gap: 8px;
		flex-wrap: wrap;
	}
	.badge {
		padding: 4px 12px;
		border-radius: 999px;
		font-weight: 600;
		background: var(--tone-neutral);
		color: var(--tone-text);
	}
	.tone-active {
		background: var(--tone-active);
	}
	.tone-good {
		background: var(--tone-good);
	}
	.tone-warning {
		background: var(--tone-warning);
	}
	.tone-danger {
		background: var(--tone-danger);
	}
	.reason,
	.hint {
		color: var(--text-muted);
		margin: 0;
	}
	dl {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
		gap: 8px;
		margin: 0;
	}
	dt {
		font-size: 0.8rem;
		color: var(--text-muted);
	}
	dd {
		margin: 0;
		font-variant-numeric: tabular-nums;
	}
	.warn {
		color: var(--tone-danger-text);
	}
	summary {
		cursor: pointer;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	details[open] summary {
		margin-bottom: 8px;
	}
</style>
