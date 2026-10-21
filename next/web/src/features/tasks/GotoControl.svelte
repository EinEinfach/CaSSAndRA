<script lang="ts">
	import type { RobotStatus } from '#features/robot/types.ts';
	import type { Point } from '#shared/viewport.ts';
	import type { GotoPicker } from './goto.svelte.ts';
	import { canStartRoute } from './plan.ts';

	let {
		picker,
		status,
		send
	}: {
		picker: GotoPicker;
		status: RobotStatus;
		/** Drives the robot to the goal. */
		send: (goal: Point) => Promise<unknown>;
	} = $props();

	let busy = $state(false);
	let error = $state('');
	const ready = $derived(canStartRoute(status));

	async function drive() {
		busy = true;
		error = '';
		try {
			await send(picker.goal!);
			picker.cancel();
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = false;
		}
	}
</script>

<section class="goto" aria-label="Go to a point">
	{#if !picker.picking}
		<button type="button" disabled={!ready} onclick={() => picker.start()}>Go to a point</button>
	{:else}
		<p class="hint" role="status">
			{picker.goal
				? `Drive to ${picker.goal.x.toFixed(2)}, ${picker.goal.y.toFixed(2)}?`
				: 'Tap the map where the robot should drive.'}
		</p>
		<div class="buttons">
			<button
				type="button"
				class="primary"
				disabled={busy || !picker.goal || !ready}
				onclick={drive}
			>
				{busy ? 'Sending…' : 'Drive there'}
			</button>
			<button type="button" disabled={busy} onclick={() => picker.cancel()}>Cancel</button>
		</div>
	{/if}
	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
</section>

<style>
	.goto {
		display: grid;
		gap: 8px;
	}
	.buttons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
