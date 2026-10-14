<script lang="ts">
	import { dockReasonLabel, gpsLabel, statusLabel, statusTone } from './format.ts';
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
				<dd data-testid="robot-battery">{state.socPercent} % · {state.batteryV.toFixed(1)} V</dd>
			</div>
			<div>
				<dt>GPS</dt>
				<dd>{gpsLabel(state.solution, state.accuracyM, state.satellites)}</dd>
			</div>
			<div>
				<dt>Mow motor</dt>
				<dd>{state.mowMotorOn ? 'on' : 'off'}</dd>
			</div>
			{#if state.sensor !== 'none'}
				<div>
					<dt>Sensor</dt>
					<dd class="warn">{state.sensor}</dd>
				</div>
			{/if}
		</dl>
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
</style>
