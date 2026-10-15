<script lang="ts" module>
	// App navigation: a rail on wide screens, a tab bar at the bottom on phones.
	export interface NavItem {
		/** Already resolved by the caller (resolve() from $app/paths). */
		href: string;
		label: string;
		icon: 'live' | 'maps' | 'settings';
	}
</script>

<script lang="ts">
	let {
		items,
		current,
		version = '',
		connected = true
	}: { items: NavItem[]; current: string; version?: string; connected?: boolean } = $props();

	const isCurrent = (href: string) =>
		href === '/' ? current === '/' : current === href || current.startsWith(href + '/');
</script>

<nav aria-label="Main">
	<div class="brand">
		<span class="logo" aria-hidden="true"></span>
		<span class="name">CaSSAndRA</span>
	</div>
	<ul>
		{#each items as item (item.href)}
			<li>
				<!-- eslint-disable-next-line svelte/no-navigation-without-resolve -- resolved by the caller -->
				<a href={item.href} aria-current={isCurrent(item.href) ? 'page' : undefined}>
					<svg viewBox="0 0 24 24" aria-hidden="true">
						{#if item.icon === 'live'}
							<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21Z" />
							<circle cx="12" cy="9.5" r="2.5" />
						{:else if item.icon === 'maps'}
							<path d="M3 6.5 9 4l6 2.5L21 4v13.5L15 20l-6-2.5L3 20Z" />
							<path d="M9 4v13.5M15 6.5V20" />
						{:else}
							<circle cx="12" cy="12" r="3" />
							<path
								d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"
							/>
						{/if}
					</svg>
					<span>{item.label}</span>
				</a>
			</li>
		{/each}
	</ul>
	<div class="meta">
		<span
			class="dot"
			class:on={connected}
			title={connected ? 'Connected to CaSSAndRA' : 'No connection to CaSSAndRA'}
		></span>
		<span class="version">{version}</span>
	</div>
</nav>

<style>
	nav {
		position: fixed;
		z-index: 20;
		left: 0;
		right: 0;
		bottom: 0;
		height: var(--nav-bottom);
		background: var(--surface);
		border-top: 1px solid var(--border);
		padding-bottom: env(safe-area-inset-bottom);
	}
	.brand,
	.meta {
		display: none;
	}
	ul {
		list-style: none;
		margin: 0;
		padding: 0;
		height: 100%;
		display: flex;
	}
	li {
		flex: 1;
	}
	a {
		height: 100%;
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		gap: 2px;
		color: var(--text-muted);
		text-decoration: none;
		font-size: 0.75rem;
		font-weight: 500;
	}
	a[aria-current='page'] {
		color: var(--accent);
	}
	svg {
		width: 24px;
		height: 24px;
		fill: none;
		stroke: currentColor;
		stroke-width: 1.8;
		stroke-linecap: round;
		stroke-linejoin: round;
	}
	@media (min-width: 900px) {
		nav {
			top: 0;
			right: auto;
			width: var(--nav-left);
			height: auto;
			display: flex;
			flex-direction: column;
			align-items: center;
			padding: 16px 0;
			border-top: none;
			border-right: 1px solid var(--border);
		}
		.brand {
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 4px;
			margin-bottom: 24px;
		}
		.logo {
			width: 32px;
			height: 32px;
			border-radius: 10px;
			background: linear-gradient(135deg, var(--accent), var(--map-border));
		}
		.name {
			font-size: 0.6rem;
			font-weight: 700;
			letter-spacing: 0.04em;
		}
		ul {
			flex-direction: column;
			gap: 6px;
			height: auto;
			width: 100%;
			padding: 0 8px;
		}
		a {
			padding: 10px 0;
			border-radius: 12px;
		}
		a:hover {
			background: var(--surface-sunken);
		}
		a[aria-current='page'] {
			background: var(--tone-active);
			color: var(--text);
		}
		.meta {
			margin-top: auto;
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 6px;
			color: var(--text-muted);
			font-size: 0.65rem;
			text-align: center;
			word-break: break-all;
			padding: 0 6px;
		}
		.dot {
			width: 8px;
			height: 8px;
			border-radius: 50%;
			background: var(--danger);
		}
		.dot.on {
			background: var(--accent);
		}
	}
</style>
