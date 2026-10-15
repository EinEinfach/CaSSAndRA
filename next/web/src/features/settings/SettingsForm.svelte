<script lang="ts">
	import { onMount } from 'svelte';
	import { fetchSettings, saveSettings } from './api.ts';
	import { emptyEdits, isDirty, passwordUpdate, type PasswordEdits } from './form.ts';
	import type { LinkKind, Secrets, Settings, SettingsUpdate, SettingsView } from './types.ts';

	let {
		load = () => fetchSettings(),
		save = (u: SettingsUpdate) => saveSettings(u)
	}: {
		load?: () => Promise<SettingsView>;
		save?: (u: SettingsUpdate) => Promise<SettingsView>;
	} = $props();

	let saved = $state<Settings | null>(null);
	let draft = $state<Settings | null>(null);
	let secrets = $state<Secrets | null>(null);
	let passwords = $state<PasswordEdits>(emptyEdits());
	let error = $state('');
	let justSaved = $state(false);
	let saving = $state(false);

	const dirty = $derived(saved !== null && draft !== null && isDirty(saved, draft, passwords));

	const links: { kind: LinkKind; title: string; detail: string }[] = [
		{ kind: 'sim', title: 'Simulator', detail: 'Try CaSSAndRA without a robot' },
		{ kind: 'http', title: 'WiFi', detail: 'HTTP to the robot' },
		{ kind: 'uart', title: 'Cable', detail: 'Serial port (UART)' },
		{ kind: 'mqtt', title: 'MQTT', detail: 'Through a bridge' }
	];

	function apply(view: SettingsView) {
		saved = structuredClone(view.settings);
		draft = structuredClone(view.settings);
		secrets = view.secrets;
		passwords = emptyEdits();
	}

	onMount(() => {
		load()
			.then(apply)
			.catch((err) => (error = err instanceof Error ? err.message : String(err)));
	});

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		if (!draft) return;
		error = '';
		justSaved = false;
		saving = true;
		try {
			apply(await save({ settings: $state.snapshot(draft), passwords: passwordUpdate(passwords) }));
			justSaved = true;
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			saving = false;
		}
	}

	function discard() {
		if (!saved) return;
		draft = structuredClone($state.snapshot(saved));
		passwords = emptyEdits();
		error = '';
	}
</script>

{#snippet password(key: keyof Secrets, label: string, numeric = false)}
	<label class="field">
		{label}
		<input
			type="password"
			autocomplete="new-password"
			inputmode={numeric ? 'numeric' : undefined}
			placeholder={secrets?.[key] ? '•••••• (unchanged)' : 'not set'}
			disabled={passwords[key].remove}
			bind:value={passwords[key].value}
		/>
	</label>
	{#if secrets?.[key]}
		<label class="switch">
			Remove {label.toLowerCase()}
			<input type="checkbox" bind:checked={passwords[key].remove} />
		</label>
	{/if}
{/snippet}

{#if draft}
	<form onsubmit={submit} aria-label="Settings">
		<section class="card wide">
			<header>
				<h2>Connection</h2>
				<p>How CaSSAndRA talks to your robot. Changes reconnect right away.</p>
			</header>
			<div class="tiles" role="radiogroup" aria-label="Connection">
				{#each links as l (l.kind)}
					<label class="tile" class:selected={draft.connection.kind === l.kind}>
						<input type="radio" name="link" value={l.kind} bind:group={draft.connection.kind} />
						<strong>{l.title}</strong>
						<span>{l.detail}</span>
					</label>
				{/each}
			</div>
			{#if draft.connection.kind === 'http'}
				<div class="grid">
					<label class="field">
						Robot URL
						<input
							type="url"
							placeholder="http://192.168.1.50"
							bind:value={draft.connection.httpUrl}
						/>
					</label>
					<div class="stack">{@render password('httpPassword', 'Robot password', true)}</div>
				</div>
			{:else if draft.connection.kind === 'uart'}
				<div class="grid">
					<label class="field">
						Serial port
						<input bind:value={draft.connection.uartPort} />
					</label>
					<label class="field">
						Baud rate
						<input type="number" min="1" bind:value={draft.connection.uartBaud} />
					</label>
				</div>
			{:else if draft.connection.kind === 'mqtt'}
				<div class="grid">
					<label class="field">
						Broker
						<input placeholder="tcp://192.168.1.10:1883" bind:value={draft.connection.mqttBroker} />
					</label>
					<label class="field">
						Mower name <span class="hint">topic prefix of the bridge</span>
						<input bind:value={draft.connection.mqttMower} />
					</label>
					<label class="field">
						Client ID
						<input bind:value={draft.connection.mqttClientId} />
					</label>
					<label class="field">
						User
						<input autocomplete="off" bind:value={draft.connection.mqttUser} />
					</label>
					<div class="stack">{@render password('mqttPassword', 'MQTT password')}</div>
				</div>
			{/if}
		</section>

		<section class="card">
			<header>
				<h2>Driving</h2>
				<p>Sent with every mow and goto command.</p>
			</header>
			<div class="grid">
				<label class="field">
					Mow speed <span class="hint">m/s</span>
					<input type="number" step="0.01" bind:value={draft.rover.mowSpeedMps} />
				</label>
				<label class="field">
					Goto speed <span class="hint">m/s</span>
					<input type="number" step="0.01" bind:value={draft.rover.gotoSpeedMps} />
				</label>
				<label class="field">
					Fix timeout <span class="hint">s without RTK fix before stopping</span>
					<input type="number" step="1" bind:value={draft.rover.fixTimeoutSec} />
				</label>
			</div>
			<label class="switch">
				Restart the task when finished
				<input type="checkbox" bind:checked={draft.rover.finishAndRestart} />
			</label>
			<label class="switch">
				Absolute position (GPS reference point)
				<input type="checkbox" bind:checked={draft.rover.absolutePosition} />
			</label>
			{#if draft.rover.absolutePosition}
				<div class="grid">
					<label class="field">
						Longitude
						<input type="number" step="any" bind:value={draft.rover.lon} />
					</label>
					<label class="field">
						Latitude
						<input type="number" step="any" bind:value={draft.rover.lat} />
					</label>
				</div>
			{/if}
		</section>

		<section class="card">
			<header>
				<h2>Battery</h2>
				<p>Turns voltage into charge level and detects charging.</p>
			</header>
			<div class="grid">
				<label class="field">
					Empty at <span class="hint">V</span>
					<input type="number" step="0.1" bind:value={draft.battery.emptyV} />
				</label>
				<label class="field">
					Full at <span class="hint">V</span>
					<input type="number" step="0.1" bind:value={draft.battery.fullV} />
				</label>
				<label class="field">
					Charging below <span class="hint">A</span>
					<input type="number" step="0.01" bind:value={draft.battery.chargingBelowA} />
				</label>
				<label class="field">
					Offline after <span class="hint">s without data</span>
					<input type="number" step="1" bind:value={draft.battery.offlineAfterSec} />
				</label>
			</div>
		</section>

		<section class="card">
			<header>
				<h2>Mow pattern</h2>
				<p>Defaults for new tasks.</p>
			</header>
			<div class="segmented" role="radiogroup" aria-label="Pattern">
				{#each ['lines', 'squares', 'rings'] as const as p (p)}
					<label class:selected={draft.planner.pattern === p}>
						<input type="radio" name="pattern" value={p} bind:group={draft.planner.pattern} />
						{p[0].toUpperCase() + p.slice(1)}
					</label>
				{/each}
			</div>
			<div class="grid">
				<label class="field">
					Lane width <span class="hint">m</span>
					<input type="number" step="0.01" bind:value={draft.planner.widthM} />
				</label>
				<label class="field">
					Angle <span class="hint">°</span>
					<input type="number" step="1" bind:value={draft.planner.angleDeg} />
				</label>
				<label class="field">
					Distance to border <span class="hint">lanes</span>
					<input type="number" step="1" bind:value={draft.planner.distanceToBorder} />
				</label>
				<label class="field">
					Border laps
					<input type="number" step="1" bind:value={draft.planner.borderLaps} />
				</label>
			</div>
			<label class="switch">
				Mow the area
				<input type="checkbox" bind:checked={draft.planner.mowArea} />
			</label>
			<label class="switch">
				Mow around exclusions
				<input type="checkbox" bind:checked={draft.planner.mowExclusions} />
			</label>
			<label class="switch">
				Border counter-clockwise
				<input type="checkbox" bind:checked={draft.planner.borderCcw} />
			</label>
		</section>

		<section class="card">
			<header>
				<h2>Home automation</h2>
				<p>MQTT API for Home Assistant, ioBroker and others.</p>
			</header>
			<label class="switch">
				MQTT API enabled
				<input type="checkbox" bind:checked={draft.api.enabled} />
			</label>
			{#if draft.api.enabled}
				<div class="grid">
					<label class="field">
						Broker
						<input placeholder="tcp://192.168.1.10:1883" bind:value={draft.api.broker} />
					</label>
					<label class="field">
						Server name <span class="hint">topic prefix</span>
						<input bind:value={draft.api.serverName} />
					</label>
					<label class="field">
						Client ID
						<input bind:value={draft.api.clientId} />
					</label>
					<label class="field">
						User
						<input autocomplete="off" bind:value={draft.api.user} />
					</label>
					<div class="stack">{@render password('apiPassword', 'API password')}</div>
				</div>
			{/if}
		</section>

		{#if dirty || error || justSaved}
			<div class="savebar" class:error={!!error}>
				{#if error}
					<p role="alert">{error}</p>
				{:else if dirty}
					<p>Unsaved changes</p>
				{:else}
					<p role="status">Saved</p>
				{/if}
				{#if dirty}
					<button type="button" onclick={discard} disabled={saving}>Discard</button>
					<button type="submit" class="primary" disabled={saving}>Save</button>
				{/if}
			</div>
		{/if}
	</form>
{:else if error}
	<p class="load-error" role="alert">{error}</p>
{:else}
	<p class="loading">Loading settings…</p>
{/if}

<style>
	form {
		display: grid;
		gap: 16px;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 340px), 1fr));
		align-items: start;
		padding-bottom: 88px; /* room for the save bar */
	}
	.card {
		display: grid;
		gap: 14px;
		min-width: 0;
	}
	.wide {
		grid-column: 1 / -1;
	}
	header h2 {
		margin: 0;
		font-size: 1.05rem;
	}
	header p {
		margin: 2px 0 0;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	.grid {
		display: grid;
		gap: 12px;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 180px), 1fr));
	}
	.stack {
		display: grid;
		gap: 10px;
		align-content: start;
	}
	.tiles {
		display: grid;
		gap: 10px;
		grid-template-columns: repeat(auto-fit, minmax(min(100%, 150px), 1fr));
	}
	.tile {
		position: relative;
		display: grid;
		gap: 2px;
		padding: 12px 14px;
		border-radius: 12px;
		border: 2px solid var(--border);
		cursor: pointer;
		transition:
			border-color 0.15s,
			background 0.15s;
	}
	.tile span {
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.tile.selected {
		border-color: var(--accent);
		background: var(--tone-active);
	}
	.tile:has(input:focus-visible),
	.segmented label:has(input:focus-visible) {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.tile input,
	.segmented input {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}
	.segmented {
		display: flex;
		padding: 4px;
		gap: 4px;
		border-radius: 12px;
		background: var(--surface-sunken);
	}
	.segmented label {
		position: relative;
		flex: 1;
		text-align: center;
		padding: 8px;
		border-radius: 9px;
		cursor: pointer;
		font-weight: 500;
	}
	.segmented label.selected {
		background: var(--surface);
		box-shadow: 0 1px 3px rgb(0 0 0 / 0.15);
	}
	.savebar {
		position: fixed;
		z-index: 10;
		left: 50%;
		bottom: calc(16px + var(--nav-bottom, 0px));
		transform: translateX(-50%);
		width: min(560px, calc(100% - 32px));
		display: flex;
		align-items: center;
		gap: 10px;
		padding: 10px 10px 10px 18px;
		border-radius: 16px;
		background: var(--text);
		color: var(--bg);
		box-shadow: var(--shadow);
	}
	/* The bar is inverted, so are its buttons. */
	.savebar button {
		background: transparent;
		color: inherit;
		border-color: currentColor;
	}
	.savebar button.primary {
		background: var(--bg);
		color: var(--text);
		border-color: var(--bg);
	}
	.savebar p {
		flex: 1;
		margin: 0;
	}
	.savebar.error {
		background: var(--danger);
		color: var(--on-danger);
	}
	.load-error {
		color: var(--tone-danger-text);
	}
	.loading {
		color: var(--text-muted);
	}
</style>
