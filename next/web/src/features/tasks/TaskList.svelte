<script lang="ts">
	import type { Task } from './types.ts';

	let {
		tasks,
		chosen,
		busy,
		toggle,
		edit,
		remove
	}: {
		tasks: Task[];
		/** IDs in the order they are mowed. */
		chosen: string[];
		busy: boolean;
		toggle: (id: string) => void;
		edit: (task: Task) => void;
		remove: (id: string) => void;
	} = $props();

	// The task whose delete button was pressed once; a second press deletes.
	let confirming = $state<string | null>(null);
</script>

{#if tasks.length === 0}
	<p class="hint">No saved tasks for this map yet. Draw one below and save it.</p>
{:else}
	<ul aria-label="Saved tasks">
		{#each tasks as task (task.id)}
			{@const order = chosen.indexOf(task.id)}
			<li class:chosen={order >= 0}>
				<label>
					<input
						type="checkbox"
						checked={order >= 0}
						onchange={() => toggle(task.id)}
						aria-label="Mow {task.name}"
					/>
					<span class="order" aria-hidden="true">{order >= 0 ? order + 1 : ''}</span>
					<span class="name">{task.name}</span>
					{#if task.parts.length > 1}
						<span class="hint">{task.parts.length} parts</span>
					{/if}
				</label>
				<div class="actions">
					{#if confirming === task.id}
						<button
							type="button"
							class="danger"
							disabled={busy}
							onclick={() => {
								confirming = null;
								remove(task.id);
							}}
						>
							Delete {task.name}?
						</button>
						<button type="button" onclick={() => (confirming = null)}>Keep</button>
					{:else}
						<button type="button" disabled={busy} onclick={() => edit(task)}>Edit</button>
						<button
							type="button"
							disabled={busy}
							onclick={() => (confirming = task.id)}
							aria-label="Delete {task.name}"
						>
							Delete
						</button>
					{/if}
				</div>
			</li>
		{/each}
	</ul>
{/if}

<style>
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 6px;
	}
	li {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 8px;
		flex-wrap: wrap;
		padding: 6px 8px;
		border-radius: 10px;
		border: 1px solid var(--border);
	}
	li.chosen {
		background: var(--tone-active);
	}
	label {
		display: flex;
		align-items: center;
		gap: 8px;
		cursor: pointer;
		min-width: 0;
		flex: 1;
	}
	input {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}
	.order {
		width: 24px;
		height: 24px;
		flex: none;
		border-radius: 50%;
		border: 1.5px solid var(--text-muted);
		display: grid;
		place-items: center;
		font-size: 0.8rem;
		font-weight: 700;
	}
	li.chosen .order {
		background: var(--text);
		border-color: var(--text);
		color: var(--surface);
	}
	label:has(input:focus-visible) .order {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.name {
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.actions {
		display: flex;
		gap: 6px;
	}
	.actions button {
		padding: 4px 10px;
		font-size: 0.85rem;
	}
</style>
