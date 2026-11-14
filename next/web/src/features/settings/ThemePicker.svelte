<script lang="ts">
	// Light, dark or like the system, for this device only; applies at once.
	import type { Theme, ThemeChoice } from '#shared/theme.svelte.ts';

	let { theme }: { theme: Theme } = $props();

	const choices: { value: ThemeChoice; label: string }[] = [
		{ value: 'system', label: 'System' },
		{ value: 'light', label: 'Light' },
		{ value: 'dark', label: 'Dark' }
	];
</script>

<section class="card" aria-label="Appearance on this device">
	<header>
		<h2>Appearance</h2>
		<p class="hint">Only on this device, saved in the browser; applies at once.</p>
	</header>
	<div class="segmented" role="radiogroup" aria-label="Theme">
		{#each choices as c (c.value)}
			<label class:selected={theme.choice === c.value}>
				<input
					type="radio"
					name="theme"
					value={c.value}
					checked={theme.choice === c.value}
					onchange={() => theme.set(c.value)}
				/>
				{c.label}
			</label>
		{/each}
	</div>
</section>

<style>
	.card {
		display: grid;
		gap: 12px;
		margin-bottom: 16px;
		max-width: 420px;
	}
	header {
		display: grid;
		gap: 2px;
	}
	h2 {
		margin: 0;
		font-size: 1.05rem;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
</style>
