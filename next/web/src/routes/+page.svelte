<script lang="ts">
	import { fetchHealth } from '#shared/api.ts';

	const health = fetchHealth();
</script>

<main>
	<h1>CaSSAndRA</h1>
	{#await health}
		<p>Verbinde…</p>
	{:then h}
		<p data-testid="health">Server {h.status} · Version {h.version}</p>
	{:catch err}
		<p data-testid="health-error" role="alert">Server nicht erreichbar: {err.message}</p>
	{/await}
</main>
