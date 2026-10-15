<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Nav, { type NavItem } from '#shared/Nav.svelte';
	import { fetchHealth } from '#shared/api.ts';
	import { EventStream } from '#shared/events.ts';
	import { provideStream } from '#shared/streamContext.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
	let version = $state('');
	let connected = $state(false);

	const stream = new EventStream();
	provideStream(stream);

	const items: NavItem[] = [
		{ href: resolve('/'), label: 'Live', icon: 'live' },
		{ href: resolve('/maps'), label: 'Maps', icon: 'maps' },
		{ href: resolve('/settings'), label: 'Settings', icon: 'settings' }
	];

	onMount(() => {
		const stop = stream.onStatus((c) => (connected = c));
		fetchHealth()
			.then((h) => (version = h.version))
			.catch(() => {});
		return () => {
			stop();
			stream.close();
		};
	});
</script>

<svelte:head>
	<link rel="icon" href="/favicon.svg" />
	<title>CaSSAndRA</title>
</svelte:head>

<Nav {items} current={page.url.pathname} {version} {connected} />
<div class="content">
	{@render children()}
</div>

<style>
	.content {
		min-height: 100dvh;
		padding-bottom: var(--nav-bottom);
	}
	@media (min-width: 900px) {
		.content {
			padding-left: var(--nav-left);
		}
	}
</style>
