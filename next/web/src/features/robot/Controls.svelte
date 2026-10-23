<script lang="ts">
	// Mow, stop and dock as icon buttons, made to float over the map.
	import { command, type SimpleCommand } from './api.ts';
	import { canDock, canStart, canStop } from './format.ts';
	import type { RobotStatus } from './types.ts';

	let {
		status,
		send = (name: SimpleCommand) => command(name)
	}: { status: RobotStatus; send?: (name: SimpleCommand) => Promise<void> } = $props();

	let busy = $state<SimpleCommand | null>(null);
	let error = $state('');

	async function run(name: SimpleCommand) {
		busy = name;
		error = '';
		try {
			await send(name);
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = null;
		}
	}
</script>

<section class="controls" aria-label="Robot controls">
	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
	<div class="buttons">
		<button
			type="button"
			class="tile mow"
			aria-label="Mow"
			title="Mow"
			disabled={!canStart(status) || busy !== null}
			onclick={() => run('mow')}
		>
			<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13l10.5-6.5Z" /></svg>
		</button>
		<!-- Stop is never blocked by another running command. -->
		<button
			type="button"
			class="tile stop"
			aria-label="Stop"
			title="Stop"
			disabled={!canStop(status)}
			onclick={() => run('stop')}
		>
			<svg viewBox="0 0 24 24" aria-hidden="true"
				><rect x="6.5" y="6.5" width="11" height="11" rx="1.5" /></svg
			>
		</button>
		<button
			type="button"
			class="tile dock"
			aria-label="Dock"
			title="Dock"
			disabled={!canDock(status) || busy !== null}
			onclick={() => run('dock')}
		>
			<svg viewBox="0 0 24 24" aria-hidden="true"
				><path d="M4 11.5 12 4.5l8 7V20h-5.5v-5.5h-5V20H4Z" /></svg
			>
		</button>
	</div>
</section>

<style>
	.controls {
		display: flex;
		align-items: flex-end;
		gap: 8px;
	}
	.buttons {
		display: flex;
		gap: 8px;
	}
	.tile {
		width: 48px;
		height: 39px;
		padding: 0;
		border-radius: 10px;
		display: grid;
		place-items: center;
		box-shadow: var(--shadow);
	}
	.tile svg {
		width: 20px;
		height: 20px;
		fill: currentColor;
	}
	.mow {
		background: var(--accent);
		border-color: var(--accent);
		color: var(--accent-text);
	}
	.stop {
		background: var(--danger);
		border-color: var(--danger);
		color: var(--on-danger);
	}
	.dock {
		background: var(--map-dock);
		border-color: var(--map-dock);
		color: #ffffff;
	}
	.error {
		margin: 0;
		max-width: 260px;
		padding: 8px 12px;
		border-radius: 10px;
		background: var(--surface);
		border: 1px solid var(--border);
		color: var(--tone-danger-text);
		font-size: 0.85rem;
		box-shadow: var(--shadow);
	}
</style>
