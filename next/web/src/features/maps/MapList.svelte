<script lang="ts">
	import { thumbnail } from './thumbnail.ts';
	import type { GardenMap } from './types.ts';

	let {
		maps,
		activeId,
		selectedId,
		onselect,
		oncreate
	}: {
		maps: GardenMap[];
		activeId: string;
		selectedId: string | null;
		onselect: (id: string) => void;
		oncreate: () => void;
	} = $props();

	const SIZE = 56;
</script>

<div class="list">
	<button type="button" class="primary new" onclick={oncreate}>+ New map</button>
	{#if maps.length === 0}
		<p class="empty">No maps yet. Draw your first one.</p>
	{/if}
	<ul aria-label="Maps">
		{#each maps as m (m.id)}
			{@const t = thumbnail(m, SIZE)}
			<li>
				<button
					type="button"
					class="item"
					class:selected={m.id === selectedId}
					aria-current={m.id === selectedId ? 'true' : undefined}
					onclick={() => onselect(m.id)}
				>
					<svg viewBox="0 0 {SIZE} {SIZE}" width={SIZE} height={SIZE} aria-hidden="true">
						<path class="lawn" d={t.perimeter} />
						{#each t.exclusions as d, i (i)}<path class="exclusion" {d} />{/each}
						<path class="dock" d={t.dock} />
					</svg>
					<span class="text">
						<span class="name">{m.name}</span>
						<span class="meta">
							{m.exclusions.length} exclusion{m.exclusions.length === 1 ? '' : 's'}
							{#if m.dock.length > 0}· dock{/if}
						</span>
					</span>
					{#if m.id === activeId}<span class="badge">On robot</span>{/if}
				</button>
			</li>
		{/each}
	</ul>
</div>

<style>
	.list {
		display: grid;
		gap: 10px;
	}
	.new {
		justify-self: start;
	}
	.empty {
		color: var(--text-muted);
		margin: 0;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
	}
	.item {
		width: 100%;
		display: flex;
		align-items: center;
		gap: 12px;
		padding: 8px;
		text-align: left;
		border: 1px solid transparent;
		border-radius: 14px;
		background: transparent;
	}
	.item:hover {
		background: var(--surface-sunken);
	}
	.item.selected {
		background: var(--surface);
		border-color: var(--accent);
	}
	svg {
		flex: none;
		border-radius: 10px;
		background: var(--map-bg);
	}
	.lawn {
		fill: var(--map-lawn);
		stroke: var(--map-border);
		stroke-width: 1;
	}
	.exclusion {
		fill: var(--map-exclusion);
	}
	.dock {
		fill: none;
		stroke: var(--map-dock);
		stroke-width: 1.5;
	}
	.text {
		flex: 1;
		min-width: 0;
		display: grid;
	}
	.name {
		font-weight: 600;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.meta {
		font-size: 0.8rem;
		color: var(--text-muted);
	}
	.badge {
		flex: none;
		font-size: 0.7rem;
		font-weight: 600;
		padding: 3px 8px;
		border-radius: 999px;
		background: var(--tone-active);
	}
</style>
