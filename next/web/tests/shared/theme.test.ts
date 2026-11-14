import { describe, expect, it, vi } from 'vitest';
import { THEME_KEY, Theme, type ThemeEnv } from '#shared/theme.svelte.ts';

function env(saved: string | null = null, systemDark = false) {
	const store = new Map<string, string>(saved === null ? [] : [[THEME_KEY, saved]]);
	let listener: ((e: { matches: boolean }) => void) | null = null;
	const e: ThemeEnv = {
		storage: {
			getItem: (k) => store.get(k) ?? null,
			setItem: (k, v) => void store.set(k, v)
		},
		media: {
			matches: systemDark,
			addEventListener: vi.fn((_: string, l: never) => (listener = l)),
			removeEventListener: vi.fn(() => (listener = null))
		} as unknown as ThemeEnv['media'],
		root: document.createElement('html')
	};
	return { env: e, store, systemChanges: (dark: boolean) => listener?.({ matches: dark }) };
}

describe('Theme', () => {
	it('follows the system until something is chosen', () => {
		const { env: e, systemChanges } = env(null, true);
		const theme = new Theme(e);
		expect(theme.choice).toBe('system');
		expect(theme.resolved).toBe('dark');
		expect(e.root.dataset.theme).toBe('dark');
		systemChanges(false);
		expect(e.root.dataset.theme).toBe('light');
	});

	it('keeps a choice on this device and ignores the system then', () => {
		const { env: e, store, systemChanges } = env(null, false);
		const theme = new Theme(e);
		theme.set('dark');
		expect(store.get(THEME_KEY)).toBe('dark');
		expect(e.root.dataset.theme).toBe('dark');
		systemChanges(false);
		expect(e.root.dataset.theme).toBe('dark');

		expect(new Theme(env('light', true).env).resolved).toBe('light');
	});

	it('ignores a broken saved value', () => {
		expect(new Theme(env('purple', true).env).choice).toBe('system');
	});

	it('works when the browser blocks storage', () => {
		const { env: e } = env();
		e.storage = {
			getItem: () => {
				throw new Error('blocked');
			},
			setItem: () => {
				throw new Error('blocked');
			}
		};
		const theme = new Theme(e);
		theme.set('dark');
		expect(e.root.dataset.theme).toBe('dark');
		const none = new Theme({ ...env().env, storage: null, media: null });
		expect(none.resolved).toBe('light');
	});

	it('stops listening to the system', () => {
		const { env: e } = env();
		new Theme(e).stop();
		expect(e.media!.removeEventListener).toHaveBeenCalled();
	});
});
