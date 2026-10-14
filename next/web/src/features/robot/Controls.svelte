<script lang="ts">
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
	<button
		type="button"
		class="primary"
		disabled={!canStart(status) || busy !== null}
		onclick={() => run('mow')}
	>
		Mow
	</button>
	<!-- Stop is never blocked by another running command. -->
	<button type="button" class="danger" disabled={!canStop(status)} onclick={() => run('stop')}
		>Stop</button
	>
	<button type="button" disabled={!canDock(status) || busy !== null} onclick={() => run('dock')}>
		Dock
	</button>
	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
</section>

<style>
	.controls {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
	}
	button {
		min-height: 48px;
		font-size: 1rem;
	}
	.error {
		grid-column: 1 / -1;
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
