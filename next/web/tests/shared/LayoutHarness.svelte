<script lang="ts">
	import MapLayout from '#shared/MapLayout.svelte';
</script>

<MapLayout label="Things to do">
	{#snippet map()}<p>the map</p>{/snippet}
	{#snippet panel()}the panel{/snippet}
</MapLayout>
