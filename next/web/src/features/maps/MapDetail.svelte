<script lang="ts" module>
	export interface DetailActions {
		upload: (id: string) => Promise<void>;
		activate: (id: string) => Promise<void>;
		remove: (id: string) => Promise<void>;
	}
</script>

<script lang="ts">
	import { activateMap, deleteMap, uploadMap } from './api.ts';
	import type { GardenMap } from './types.ts';

	let {
		map,
		active,
		onedit,
		onduplicate,
		ondeleted = () => {},
		actions = {
			upload: (id) => uploadMap(id),
			activate: (id) => activateMap(id),
			remove: (id) => deleteMap(id)
		}
	}: {
		map: GardenMap;
		active: boolean;
		onedit: () => void;
		onduplicate: () => void;
		ondeleted?: () => void;
		actions?: DetailActions;
	} = $props();

	let busy = $state<'' | 'upload' | 'activate' | 'delete'>('');
	let message = $state('');
	let error = $state('');
	let confirmDelete = $state(false);

	async function run(kind: 'upload' | 'activate' | 'delete', done: string) {
		busy = kind;
		error = '';
		message = '';
		try {
			if (kind === 'upload') await actions.upload(map.id);
			if (kind === 'activate') await actions.activate(map.id);
			if (kind === 'delete') {
				await actions.remove(map.id);
				ondeleted();
			}
			message = done;
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			busy = '';
			confirmDelete = false;
		}
	}

	// Only a different map clears the messages, not an update of the same one.
	const mapId = $derived(map.id);
	$effect(() => {
		void mapId;
		message = '';
		error = '';
		confirmDelete = false;
	});
</script>

<section class="detail" aria-label={map.name}>
	<header>
		<div>
			<h2>{map.name}</h2>
			<p>
				{map.perimeter.length} perimeter points · {map.exclusions.length} exclusions · dock path {map
					.dock.length > 0
					? `${map.dock.length} points`
					: 'missing'}
			</p>
		</div>
		{#if active}<span class="badge">On robot</span>{/if}
	</header>

	<div class="actions">
		<button
			type="button"
			class="primary"
			disabled={busy !== ''}
			onclick={() => run('upload', 'Sent to the robot.')}
		>
			{busy === 'upload' ? 'Sending…' : 'Send to robot'}
		</button>
		<button type="button" disabled={busy !== ''} onclick={onedit}>Edit</button>
		<button type="button" disabled={busy !== ''} onclick={onduplicate}>Duplicate</button>
		{#if !active}
			<button
				type="button"
				disabled={busy !== ''}
				onclick={() => run('activate', 'Shown on the live view.')}
			>
				Show on live view
			</button>
		{/if}
		<span class="spacer"></span>
		{#if confirmDelete}
			<button type="button" class="danger" disabled={busy !== ''} onclick={() => run('delete', '')}>
				Really delete
			</button>
			<button type="button" onclick={() => (confirmDelete = false)}>Keep</button>
		{:else}
			<button
				type="button"
				class="ghost-danger"
				disabled={busy !== ''}
				onclick={() => (confirmDelete = true)}
			>
				Delete
			</button>
		{/if}
	</div>
	{#if message}<p class="message" role="status">{message}</p>{/if}
	{#if error}<p class="error" role="alert">{error}</p>{/if}
</section>

<style>
	.detail {
		display: grid;
		gap: 12px;
	}
	header {
		display: flex;
		align-items: start;
		justify-content: space-between;
		gap: 12px;
	}
	h2 {
		margin: 0;
		font-size: 1.3rem;
	}
	header p {
		margin: 2px 0 0;
		color: var(--text-muted);
		font-size: 0.9rem;
	}
	.badge {
		font-size: 0.75rem;
		font-weight: 600;
		padding: 4px 10px;
		border-radius: 999px;
		background: var(--tone-active);
		white-space: nowrap;
	}
	.actions {
		display: flex;
		flex-wrap: wrap;
		gap: 8px;
	}
	.spacer {
		flex: 1;
	}
	.ghost-danger {
		color: var(--tone-danger-text);
	}
	.message {
		margin: 0;
		color: var(--accent);
	}
	.error {
		margin: 0;
		color: var(--tone-danger-text);
	}
</style>
