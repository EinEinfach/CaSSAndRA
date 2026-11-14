<script lang="ts">
	import SettingsForm from '#features/settings/SettingsForm.svelte';
	import ThemePicker from '#features/settings/ThemePicker.svelte';
	import { useTheme } from '#shared/theme.svelte.ts';

	const theme = useTheme();
</script>

<svelte:head>
	<title>Settings · CaSSAndRA</title>
</svelte:head>

<div class="page">
	<h1>Settings</h1>
	{#if theme}<ThemePicker {theme} />{/if}
	<SettingsForm />
</div>

<style>
	.page {
		max-width: 1100px;
		margin: 0 auto;
		padding: 20px 16px;
	}
	h1 {
		margin: 0 0 16px;
		font-size: 1.6rem;
	}
</style>
