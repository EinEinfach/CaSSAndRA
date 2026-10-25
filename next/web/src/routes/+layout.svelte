<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import { resolve } from '$app/paths';
	import { page } from '$app/state';
	import Nav, { type NavItem } from '#shared/Nav.svelte';
	import { fetchHealth } from '#shared/api.ts';
	import { EventStream } from '#shared/events.ts';
	import { provideRobotPicture, RobotPictureSource } from '#shared/robotPicture.svelte.ts';
	import { provideStream } from '#shared/streamContext.ts';
	import type { SettingsView } from '#features/settings/types.ts';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
	let version = $state('');
	let connected = $state(false);

	const stream = new EventStream();
	provideStream(stream);
	const robotPicture = new RobotPictureSource();
	provideRobotPicture(robotPicture);

	const items: NavItem[] = [
		{ href: resolve('/'), label: 'Live', icon: 'live' },
		{ href: resolve('/tasks'), label: 'Tasks', icon: 'tasks' },
		{ href: resolve('/schedule'), label: 'Schedule', icon: 'schedule' },
		{ href: resolve('/maps'), label: 'Maps', icon: 'maps' },
		{ href: resolve('/settings'), label: 'Settings', icon: 'settings' }
	];

	onMount(() => {
		const stops = [
			stream.onStatus((c) => (connected = c)),
			stream.on<SettingsView>('settings', ({ settings: { appearance } }) =>
				robotPicture.set(appearance.robotPicture, appearance.robotSizeCm)
			)
		];
		fetchHealth()
			.then((h) => (version = h.version))
			.catch(() => {});
		return () => {
			stops.forEach((stop) => stop());
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
