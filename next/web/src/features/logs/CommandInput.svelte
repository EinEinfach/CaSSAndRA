<script lang="ts">
	// Sends a typed AT+ command to the robot once and shows its reply (legacy
	// "custom command"). Some commands move the robot; nothing is repeated.
	import { commandProblem, normalizeCommand } from './command.ts';

	let { send }: { send: (line: string) => Promise<string> } = $props();

	interface Sent {
		id: number;
		line: string;
		reply?: string;
		error?: string;
	}

	let line = $state('');
	let busy = $state(false);
	let sent = $state<Sent[]>([]);
	let nextId = 0;

	const problem = $derived(commandProblem(line));

	async function submit(ev: SubmitEvent) {
		ev.preventDefault();
		if (busy || problem || line.trim() === '') return;
		const entry: Sent = { id: nextId++, line: normalizeCommand(line) };
		busy = true;
		try {
			entry.reply = await send(entry.line);
			line = '';
		} catch (err) {
			entry.error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = false;
			sent = [entry, ...sent].slice(0, 20);
		}
	}
</script>

<section class="card" aria-labelledby="command-title">
	<h2 id="command-title">Robot command</h2>
	<p class="hint">
		Goes to the robot once, as typed, e.g. <code>AT+V</code> or <code>AT+S</code>. Some commands
		make it move.
	</p>
	<form onsubmit={submit}>
		<input
			class="text"
			aria-label="AT command"
			placeholder="AT+V"
			autocomplete="off"
			autocapitalize="characters"
			spellcheck="false"
			bind:value={line}
		/>
		<button type="submit" disabled={busy || problem !== '' || line.trim() === ''}>
			{busy ? 'Sending…' : 'Send'}
		</button>
	</form>
	{#if problem}
		<p class="error">{problem}</p>
	{/if}
	{#if sent.length > 0}
		<ol class="sent" aria-label="Sent commands">
			{#each sent as s (s.id)}
				<li>
					<code>{s.line}</code>
					{#if s.error}
						<span class="error">{s.error}</span>
					{:else}
						<code class="reply">{s.reply || '(no reply)'}</code>
					{/if}
				</li>
			{/each}
		</ol>
	{/if}
</section>

<style>
	section {
		display: grid;
		gap: 10px;
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
	}
	form {
		display: flex;
		gap: 8px;
	}
	input {
		flex: 1;
		min-width: 0;
		font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.sent {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
		font-size: 0.8rem;
	}
	.sent li {
		display: grid;
		gap: 2px;
	}
	.reply {
		color: var(--text-muted);
		overflow-wrap: anywhere;
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
		font-size: 0.85rem;
	}
</style>
