<script lang="ts">
	import { followsRoute, routeProgress } from './route.ts';
	import type { RobotStatus } from './types.ts';

	let {
		status,
		mowPointIndex,
		routeLength,
		skipNext,
		skipTo
	}: {
		status: RobotStatus;
		mowPointIndex: number;
		routeLength: number;
		skipNext: () => Promise<void>;
		/** Continues at a fraction (0..1) of the route. */
		skipTo: (fraction: number) => Promise<void>;
	} = $props();

	const percent = $derived(Math.round(routeProgress(mowPointIndex, routeLength) * 100));
	const active = $derived(followsRoute(status) && routeLength > 0);
	// The slider's choice; null follows the robot.
	let target = $state<number | null>(null);
	let busy = $state(false);
	let error = $state('');

	async function run(action: () => Promise<void>) {
		busy = true;
		error = '';
		try {
			await action();
			target = null;
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = false;
		}
	}
</script>

{#if active}
	<section class="progress" aria-label="Route progress">
		<div class="head">
			<span>Progress</span>
			<strong data-testid="route-progress">{percent} %</strong>
		</div>
		<div
			class="bar"
			role="progressbar"
			aria-valuenow={percent}
			aria-valuemin={0}
			aria-valuemax={100}
		>
			<div style:width="{percent}%"></div>
		</div>
		<label class="jump">
			<span>Jump to {target ?? percent} %</span>
			<input
				type="range"
				min="0"
				max="100"
				step="1"
				value={target ?? percent}
				oninput={(e) => (target = Number(e.currentTarget.value))}
				aria-label="Jump to progress"
			/>
		</label>
		<div class="buttons">
			<button
				type="button"
				disabled={busy || target === null}
				onclick={() => run(() => skipTo(target! / 100))}
			>
				Jump
			</button>
			<button type="button" disabled={busy} onclick={() => run(skipNext)}>Skip point</button>
		</div>
		{#if error}
			<p class="error" role="alert">{error}</p>
		{/if}
	</section>
{/if}

<style>
	.progress {
		display: grid;
		gap: 8px;
	}
	.head {
		display: flex;
		justify-content: space-between;
		color: var(--text-muted);
	}
	.head strong {
		color: var(--text);
	}
	.bar {
		height: 8px;
		border-radius: 4px;
		background: var(--surface-sunken);
		overflow: hidden;
	}
	.bar div {
		height: 100%;
		background: var(--text);
	}
	.jump {
		display: grid;
		gap: 4px;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.jump input {
		width: 100%;
		accent-color: var(--text);
	}
	.buttons {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 8px;
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
