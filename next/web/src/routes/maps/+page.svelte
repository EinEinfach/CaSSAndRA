<script lang="ts">
	import { onMount, tick } from 'svelte';
	import MapDetail from '#features/maps/MapDetail.svelte';
	import MapEditor from '#features/maps/MapEditor.svelte';
	import MapList from '#features/maps/MapList.svelte';
	import { createMap, updateMap } from '#features/maps/api.ts';
	import { emptyShape } from '#features/maps/editor.ts';
	import { MapsStore } from '#features/maps/store.svelte.ts';
	import type { MapShape } from '#features/maps/types.ts';
	import { RobotStore } from '#features/robot/store.svelte.ts';
	import MapCanvas from '#shared/MapCanvas.svelte';
	import MapLayout from '#shared/MapLayout.svelte';
	import { useStream } from '#shared/streamContext.ts';

	const stream = useStream();
	const store = new MapsStore();
	const robot = new RobotStore();

	let selectedId = $state<string | null>(null);
	// The editor: which map (null = a new one) and what it starts with.
	let editing = $state<{ id: string | null; initial: MapShape; title: string } | null>(null);

	const selected = $derived(
		(selectedId && store.byId(selectedId)) || store.active || store.maps[0] || null
	);
	const robotPosition = $derived(
		robot.state && robot.state.status !== 'offline' ? robot.state.position : null
	);

	onMount(() => {
		const stops = [store.connect(stream), robot.connect(stream)];
		return () => stops.forEach((stop) => stop());
	});

	const shapeOf = (m: MapShape): MapShape => ({
		name: m.name,
		perimeter: m.perimeter,
		exclusions: m.exclusions,
		dock: m.dock,
		searchWire: m.searchWire
	});

	let mapView = $state<HTMLElement>();

	async function select(id: string) {
		selectedId = id;
		// On phones the map sits above the list.
		if (!window.matchMedia('(min-width: 900px)').matches) {
			await tick();
			mapView?.scrollIntoView({ behavior: 'smooth', block: 'start' });
		}
	}

	const layers = $derived(
		selected
			? {
					perimeter: selected.perimeter,
					exclusions: selected.exclusions,
					dock: selected.dock,
					searchWire: selected.searchWire
				}
			: {}
	);

	async function save(shape: MapShape) {
		const saved = editing?.id ? await updateMap(editing.id, shape) : await createMap(shape);
		selectedId = saved.id;
		editing = null;
	}
</script>

<svelte:head>
	<title>Maps · CaSSAndRA</title>
</svelte:head>

{#if editing}
	{#key editing}
		<MapEditor
			initial={editing.initial}
			title={editing.title}
			{robotPosition}
			{save}
			cancel={() => (editing = null)}
		/>
	{/key}
{:else}
	<MapLayout label="Maps">
		{#snippet map()}
			<div class="view" bind:this={mapView}>
				<MapCanvas {layers} label={selected ? `Map ${selected.name}` : 'Map'} />
			</div>
		{/snippet}
		{#snippet panel()}
			<h1>Maps</h1>
			{#if selected}
				<MapDetail
					map={selected}
					active={selected.id === store.activeId}
					onedit={() =>
						(editing = {
							id: selected.id,
							initial: shapeOf(selected),
							title: `Editing ${selected.name}`
						})}
					onduplicate={() =>
						(editing = {
							id: null,
							initial: { ...shapeOf(selected), name: `${selected.name} (copy)` },
							title: `Copy of ${selected.name}`
						})}
					ondeleted={() => (selectedId = null)}
				/>
			{:else if store.loaded}
				<div class="empty">
					<h2>Draw your garden</h2>
					<p>
						Create a map with the perimeter of your lawn, the areas to leave out and the path into
						the docking station. You can walk the robot along the border and add its position as
						points.
					</p>
					<button
						type="button"
						class="primary"
						onclick={() => (editing = { id: null, initial: emptyShape(), title: 'New map' })}
					>
						Create a map
					</button>
				</div>
			{/if}
			<MapList
				maps={store.maps}
				activeId={store.activeId}
				selectedId={selected?.id ?? null}
				onselect={select}
				oncreate={() => (editing = { id: null, initial: emptyShape(), title: 'New map' })}
			/>
		{/snippet}
	</MapLayout>
{/if}

<style>
	h1 {
		margin: 0;
		font-size: 1.6rem;
	}
	.view {
		height: 100%;
		scroll-margin-top: 16px;
	}
	.empty {
		display: grid;
		justify-items: start;
		gap: 8px;
	}
	.empty h2 {
		margin: 0;
	}
	.empty p {
		margin: 0 0 8px;
		color: var(--text-muted);
	}
</style>
