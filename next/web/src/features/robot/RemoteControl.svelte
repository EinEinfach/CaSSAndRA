<script lang="ts">
	// Mow motor, speed and system commands (legacy "remote control").
	import { command, setMowMotor, setSpeed } from './api.ts';
	import {
		canChangeSpeed,
		canSendRemote,
		formatSpeed,
		mowMotorOnConfirmation,
		nextSpeed,
		speedLabel,
		systemCommands,
		type Confirmation,
		type SystemCommand
	} from './remote.ts';
	import type { RobotStatus } from './types.ts';

	export interface RemoteActions {
		setMowMotor: (on: boolean) => Promise<void>;
		setSpeed: (mps: number) => Promise<void>;
		command: (name: SystemCommand) => Promise<void>;
	}

	let {
		status,
		mowMotorOn,
		speedMps,
		actions = { setMowMotor, setSpeed, command }
	}: {
		status: RobotStatus;
		mowMotorOn: boolean;
		speedMps: number;
		actions?: RemoteActions;
	} = $props();

	let busy = $state(false);
	let error = $state('');
	let pending = $state<{ confirm: Confirmation; run: () => Promise<void> } | null>(null);

	const reachable = $derived(canSendRemote(status));
	const speedShown = $derived(canChangeSpeed(status) && speedMps > 0);

	async function run(action: () => Promise<void>) {
		pending = null;
		busy = true;
		error = '';
		try {
			await action();
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = false;
		}
	}

	function toggleMowMotor(e: Event & { currentTarget: HTMLInputElement }) {
		// The switch shows what the robot does, not the click: put it back until it is confirmed.
		e.currentTarget.checked = mowMotorOn;
		if (mowMotorOn) {
			void run(() => actions.setMowMotor(false));
		} else {
			pending = { confirm: mowMotorOnConfirmation, run: () => actions.setMowMotor(true) };
		}
	}

	function ask(name: SystemCommand) {
		const cmd = systemCommands.find((c) => c.name === name)!;
		pending = { confirm: cmd.confirm, run: () => actions.command(name) };
	}
</script>

<section class="remote" aria-label="Remote control">
	<label class="switch">
		<span>Mow motor</span>
		<input
			type="checkbox"
			role="switch"
			checked={mowMotorOn}
			disabled={!reachable || busy}
			onchange={toggleMowMotor}
		/>
	</label>

	{#if speedShown}
		<div class="speed">
			<span>{speedLabel(status)}</span>
			<div class="stepper">
				<button
					type="button"
					aria-label="Slower"
					disabled={busy}
					onclick={() => run(() => actions.setSpeed(nextSpeed(speedMps, -1)))}>−</button
				>
				<strong data-testid="robot-speed">{formatSpeed(speedMps)}</strong>
				<button
					type="button"
					aria-label="Faster"
					disabled={busy}
					onclick={() => run(() => actions.setSpeed(nextSpeed(speedMps, 1)))}>+</button
				>
			</div>
		</div>
	{/if}

	{#if pending}
		<div class="confirm" role="alertdialog" aria-label="Confirm">
			<p>{pending.confirm.question}</p>
			<div class="buttons">
				<button type="button" onclick={() => (pending = null)}>Cancel</button>
				<button
					type="button"
					class={pending.confirm.danger ? 'danger' : 'primary'}
					disabled={busy}
					onclick={() => run(pending!.run)}>{pending.confirm.confirmLabel}</button
				>
			</div>
		</div>
	{:else}
		<div class="system">
			{#each systemCommands as cmd (cmd.name)}
				<button type="button" disabled={!reachable || busy} onclick={() => ask(cmd.name)}
					>{cmd.label}</button
				>
			{/each}
		</div>
	{/if}

	{#if error}
		<p class="error" role="alert">{error}</p>
	{/if}
</section>

<style>
	.remote {
		display: grid;
		gap: 12px;
	}
	.speed {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 12px;
	}
	.stepper {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.stepper button {
		width: 40px;
		padding: 6px 0;
		font-size: 1.1rem;
		line-height: 1;
	}
	.stepper strong {
		min-width: 5.5em;
		text-align: center;
		font-variant-numeric: tabular-nums;
	}
	.system {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 8px;
	}
	.system button {
		padding: 8px 6px;
		font-size: 0.85rem;
	}
	.confirm {
		display: grid;
		gap: 8px;
		padding: 12px;
		border-radius: 12px;
		background: var(--surface-sunken);
	}
	.confirm p {
		margin: 0;
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
