// Light or dark: per device, so the phone can be dark while the PC is light.
// The choice lives in the browser (localStorage), not in the settings on the
// server. app.html sets the theme before the first paint with the same key.
import { getContext, setContext } from 'svelte';

export type ThemeChoice = 'system' | 'light' | 'dark';
export type ResolvedTheme = 'light' | 'dark';

export const THEME_KEY = 'cassandra.theme';

export interface ThemeEnv {
	/** null where the browser blocks storage (private mode). */
	storage: Pick<Storage, 'getItem' | 'setItem'> | null;
	/** prefers-color-scheme: dark */
	media: Pick<MediaQueryList, 'matches' | 'addEventListener' | 'removeEventListener'> | null;
	root: HTMLElement;
}

export function browserThemeEnv(): ThemeEnv {
	let storage: ThemeEnv['storage'] = null;
	try {
		storage = window.localStorage;
	} catch {
		// blocked: the choice lasts until the page is closed
	}
	return {
		storage,
		media: window.matchMedia?.('(prefers-color-scheme: dark)') ?? null,
		root: document.documentElement
	};
}

const isChoice = (v: unknown): v is ThemeChoice => v === 'system' || v === 'light' || v === 'dark';

export class Theme {
	choice = $state<ThemeChoice>('system');
	private systemDark = $state(false);
	private readonly onSystem = (e: { matches: boolean }) => {
		this.systemDark = e.matches;
		this.apply();
	};

	constructor(private env: ThemeEnv) {
		let saved: string | null = null;
		try {
			saved = env.storage?.getItem(THEME_KEY) ?? null;
		} catch {
			// storage failing on read: keep the system theme
		}
		if (isChoice(saved)) this.choice = saved;
		this.systemDark = env.media?.matches ?? false;
		env.media?.addEventListener('change', this.onSystem);
		this.apply();
	}

	/** What is shown now. Canvases read it to redraw with the new colors. */
	get resolved(): ResolvedTheme {
		if (this.choice !== 'system') return this.choice;
		return this.systemDark ? 'dark' : 'light';
	}

	set(choice: ThemeChoice): void {
		this.choice = choice;
		try {
			this.env.storage?.setItem(THEME_KEY, choice);
		} catch {
			// not stored: it still applies until the page is closed
		}
		this.apply();
	}

	stop(): void {
		this.env.media?.removeEventListener('change', this.onSystem);
	}

	// Synchronously, so the colors are there before effects that read them run.
	private apply(): void {
		this.env.root.dataset.theme = this.resolved;
	}
}

const key = Symbol('theme');

export function provideTheme(theme: Theme): void {
	setContext(key, theme);
}

/** The layout's theme, or null outside the layout (e.g. in tests). */
export function useTheme(): Theme | null {
	return getContext<Theme | undefined>(key) ?? null;
}
