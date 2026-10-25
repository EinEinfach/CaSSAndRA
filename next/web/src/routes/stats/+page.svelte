<script lang="ts">
	import StatsView from '#features/stats/StatsView.svelte';
</script>

<svelte:head>
	<title>Statistics · CaSSAndRA</title>
</svelte:head>

<div class="page">
	<h1>Statistics</h1>
	<StatsView />
</div>

<style>
	.page {
		max-width: 1100px;
		margin: 0 auto;
		padding: 20px 16px;
	}
	h1 {
		margin: 0 0 16px;
		font-size: 1.6rem;
	}
</style>
