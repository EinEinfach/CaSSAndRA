import { describe, expect, it, vi } from 'vitest';
import { filterEntries, formatTime, LogFeed } from '#features/logs/feed.svelte.ts';
import type { LogEntry } from '#features/logs/types.ts';
import { entry, manualScheduler } from './fixtures.ts';

const settle = () => new Promise((r) => setTimeout(r, 0));

describe('filterEntries', () => {
	const all = [
		entry(1, 'link online', 'DEBUG'),
		entry(2, 'command cmd=mow'),
		entry(3, 'offline', 'WARN'),
		entry(4, 'broken', 'ERROR')
	];

	it.each([
		['', 'DEBUG', [1, 2, 3, 4]],
		['', 'INFO', [2, 3, 4]],
		['', 'WARN', [3, 4]],
		['', 'ERROR', [4]],
		['CMD=MOW', 'DEBUG', [2]],
		['  line ', 'DEBUG', [1, 3]],
		['line', 'INFO', [3]]
	] as const)('query %j at %s', (query, level, want) => {
		expect(filterEntries(all, query, level).map((e) => e.seq)).toEqual(want);
	});
});

describe('formatTime', () => {
	it('shows local hours, minutes and seconds', () => {
		const d = new Date(2026, 10, 14, 9, 5, 7);
		expect(formatTime(d.toISOString())).toBe('09:05:07');
		expect(formatTime('nonsense')).toBe('');
	});
});

describe('LogFeed', () => {
	function setup(pages: LogEntry[][]) {
		const load = vi.fn(async (after: number) => {
			void after;
			return pages.shift() ?? [];
		});
		const scheduler = manualScheduler();
		return { feed: new LogFeed(load, scheduler, 1000, 3), load, scheduler };
	}

	it('loads at start and asks for newer records on each tick', async () => {
		const { feed, load, scheduler } = setup([[entry(1), entry(2)], [entry(3)]]);
		feed.start();
		await settle();
		expect(feed.entries.map((e) => e.seq)).toEqual([1, 2]);
		scheduler.tick();
		await settle();
		expect(load).toHaveBeenLastCalledWith(2);
		expect(feed.entries.map((e) => e.seq)).toEqual([1, 2, 3]);
		feed.stop();
		expect(scheduler.active).toBe(0);
	});

	it('keeps at most max entries and drops repeated ones', async () => {
		const { feed } = setup([
			[entry(1), entry(2)],
			[entry(2), entry(3), entry(4)]
		]);
		await feed.poll();
		await feed.poll();
		expect(feed.entries.map((e) => e.seq)).toEqual([2, 3, 4]);
	});

	it('does not load while paused and catches up on resume', async () => {
		const { feed, load } = setup([[entry(1)], [entry(2), entry(3)]]);
		await feed.poll();
		feed.togglePause();
		await feed.poll();
		expect(load).toHaveBeenCalledTimes(1);
		feed.togglePause();
		await settle();
		expect(feed.entries.map((e) => e.seq)).toEqual([1, 2, 3]);
	});

	it('clears without getting the old lines back', async () => {
		const { feed, load } = setup([[entry(1), entry(2)], [entry(3)]]);
		await feed.poll();
		feed.clear();
		expect(feed.entries).toEqual([]);
		await feed.poll();
		expect(load).toHaveBeenLastCalledWith(2);
		expect(feed.entries.map((e) => e.seq)).toEqual([3]);
	});

	it('shows an error until loading works again', async () => {
		const load = vi
			.fn<(after: number) => Promise<LogEntry[]>>()
			.mockRejectedValueOnce(new Error('offline'))
			.mockResolvedValueOnce([entry(1)]);
		const feed = new LogFeed(load, manualScheduler());
		await feed.poll();
		expect(feed.error).toBe('offline');
		await feed.poll();
		expect(feed.error).toBe('');
		expect(feed.entries).toHaveLength(1);
	});
});
