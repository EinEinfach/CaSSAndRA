<script lang="ts">
	// The weekly schedule: per day a window and the tasks to mow in it.
	import { untrack } from 'svelte';
	import type { Task } from '#features/tasks/types.ts';
	import { describe, isDayOff, isDirty, setDayOn, setStart, timeOptions } from './schedule.ts';
	import { weekdays, type Schedule, type ScheduleView } from './types.ts';

	let {
		view,
		tasks,
		maps,
		activeMapId,
		save,
		now = new Date()
	}: {
		/** null until the first event arrived. */
		view: ScheduleView | null;
		tasks: Task[];
		maps: { id: string; name: string }[];
		activeMapId: string | undefined;
		save: (s: Schedule) => Promise<ScheduleView>;
		now?: Date;
	} = $props();

	/** The schedule the draft started from: the last one received or saved. */
	let base = $state.raw<Schedule | null>(null);
	let draft = $state<Schedule | null>(null);
	let error = $state('');
	let saving = $state(false);
	let justSaved = $state(false);

	const dirty = $derived(base !== null && draft !== null && isDirty(base, draft));

	// Follow changes from elsewhere while nothing is edited here.
	$effect(() => {
		const s = view?.schedule;
		if (!s) return;
		untrack(() => {
			if (draft === null || !dirty) {
				base = s;
				draft = structuredClone(s);
			}
		});
	});

	const taskById = $derived(new Map(tasks.map((t) => [t.id, t])));
	const mapName = (id: string) => maps.find((m) => m.id === id)?.name ?? 'a deleted map';

	/** The map the tasks of day i come from: the one of its tasks, else the active map. */
	function dayMap(i: number): string | undefined {
		const first = draft?.days[i].taskIds.map((id) => taskById.get(id)).find((t) => t);
		return first?.mapId ?? activeMapId;
	}

	function addTask(i: number, id: string) {
		if (!draft || !id) return;
		draft.days[i].taskIds.push(id);
	}

	function removeTask(i: number, id: string) {
		if (!draft) return;
		draft.days[i].taskIds = draft.days[i].taskIds.filter((t) => t !== id);
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		if (!draft) return;
		error = '';
		justSaved = false;
		saving = true;
		try {
			const v = await save($state.snapshot(draft));
			base = v.schedule;
			draft = structuredClone(v.schedule);
			justSaved = true;
		} catch (err) {
			error = err instanceof Error ? err.message : String(err);
		} finally {
			saving = false;
		}
	}

	function discard() {
		if (base) draft = structuredClone(base);
		error = '';
	}
</script>

{#if draft && view}
	<form onsubmit={submit} aria-label="Schedule">
		<section class="card head">
			<label class="switch">
				<span>
					<strong>Mow by schedule</strong>
					<span class="hint"
						>Starts the tasks of the day when its window opens and sends the robot home when it
						closes.</span
					>
				</span>
				<input type="checkbox" bind:checked={draft.active} />
			</label>
			<p
				class="status"
				data-state={view.status.state}
				data-testid="schedule-status"
				aria-live="polite"
			>
				{describe(view.status, now)}
			</p>
		</section>

		<ol class="days">
			{#each draft.days as day, i (i)}
				{@const off = isDayOff(day)}
				{@const mapId = dayMap(i)}
				{@const choices = tasks.filter((t) => t.mapId === mapId && !day.taskIds.includes(t.id))}
				<li class="card day" class:off>
					<div class="row">
						<label class="switch day-name">
							<strong>{weekdays[i]}</strong>
							<input
								type="checkbox"
								aria-label="Mow on {weekdays[i]}"
								checked={!off}
								onchange={(e) => (draft!.days[i] = setDayOn(day, e.currentTarget.checked))}
							/>
						</label>
						{#if !off}
							<div class="window">
								<select
									aria-label="{weekdays[i]} from"
									value={day.start}
									onchange={(e) => (draft!.days[i] = setStart(day, e.currentTarget.value))}
								>
									{#each timeOptions(day.start).filter((t) => t !== '24:00') as t (t)}
										<option value={t}>{t}</option>
									{/each}
								</select>
								<span aria-hidden="true">–</span>
								<select aria-label="{weekdays[i]} until" bind:value={draft.days[i].end}>
									{#each timeOptions(day.end).filter((t) => t > day.start) as t (t)}
										<option value={t}>{t}</option>
									{/each}
								</select>
							</div>
						{/if}
					</div>
					{#if !off}
						<div class="tasks">
							{#each day.taskIds as id, n (id)}
								{@const task = taskById.get(id)}
								<span class="chip">
									<span class="order">{n + 1}</span>
									<span class="name">{task?.name ?? 'Deleted task'}</span>
									<button
										type="button"
										class="remove"
										aria-label="Remove {task?.name ?? 'task'} from {weekdays[i]}"
										onclick={() => removeTask(i, id)}>×</button
									>
								</span>
							{/each}
							{#if choices.length > 0}
								<select
									class="add"
									aria-label="Add a task on {weekdays[i]}"
									value=""
									onchange={(e) => {
										addTask(i, e.currentTarget.value);
										e.currentTarget.value = '';
									}}
								>
									<option value="">+ Task</option>
									{#each choices as t (t.id)}
										<option value={t.id}>{t.name}</option>
									{/each}
								</select>
							{/if}
						</div>
						{#if day.taskIds.length === 0}
							<p class="hint">No tasks: the robot continues the route it has.</p>
						{:else if mapId !== activeMapId}
							<p class="hint warn">
								These tasks belong to {mapName(mapId ?? '')}; they only start while it is the active
								map.
							</p>
						{/if}
					{/if}
				</li>
			{/each}
		</ol>

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
{:else}
	<p class="loading">Loading the schedule…</p>
{/if}

<style>
	form {
		display: flex;
		flex-direction: column;
		gap: 16px;
		padding-bottom: 80px; /* room for the save bar */
	}
	.head {
		display: flex;
		flex-direction: column;
		gap: 12px;
	}
	.head .switch > span {
		display: flex;
		flex-direction: column;
		gap: 2px;
	}
	.status {
		margin: 0;
		color: var(--text-muted);
	}
	.status[data-state='started'] {
		color: var(--text);
		font-weight: 600;
	}
	.status[data-state='failed'] {
		color: var(--tone-danger-text);
	}
	.days {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 10px;
	}
	.day {
		display: flex;
		flex-direction: column;
		gap: 10px;
	}
	.day.off {
		color: var(--text-muted);
	}
	.row {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 10px 16px;
	}
	.day-name {
		flex: 0 0 170px;
	}
	.window {
		display: flex;
		align-items: center;
		gap: 8px;
	}
	.tasks {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 6px;
	}
	.chip {
		display: inline-flex;
		align-items: center;
		gap: 6px;
		padding: 4px 4px 4px 6px;
		border: 1px solid var(--border);
		border-radius: 999px;
		background: var(--tone-neutral);
		font-size: 0.9rem;
	}
	.order {
		display: inline-grid;
		place-items: center;
		width: 20px;
		height: 20px;
		border-radius: 50%;
		background: var(--text);
		color: var(--bg);
		font-size: 0.75rem;
	}
	.remove {
		border: none;
		background: none;
		padding: 0 6px;
		font-size: 1rem;
		line-height: 1;
		color: var(--text-muted);
	}
	select {
		font: inherit;
		color: var(--text);
		background: var(--surface-sunken);
		border: 1px solid transparent;
		border-radius: 10px;
		padding: 8px 10px;
		font-variant-numeric: tabular-nums;
	}
	select:focus {
		outline: none;
		border-color: var(--accent);
		background: var(--surface);
	}
	.day.off strong {
		font-weight: 500;
	}
	.hint {
		margin: 0;
		color: var(--text-muted);
		font-size: 0.85rem;
	}
	.warn {
		padding: 6px 10px;
		border-radius: 8px;
		background: var(--tone-warning);
		color: var(--tone-text);
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
	.loading {
		color: var(--text-muted);
	}
</style>
