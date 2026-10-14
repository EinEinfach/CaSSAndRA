<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { drawMap, mapPoints, type MapColors, type MapLayers } from './drawMap.ts';
	import { fit, pan, resize, zoomAt, type Viewport } from './viewport.ts';

	interface Props {
		layers: MapLayers;
		label?: string;
	}
	let { layers, label = 'Map' }: Props = $props();

	let canvas: HTMLCanvasElement;
	let vp = $state<Viewport>(fit([], 300, 300));
	let userMoved = $state(false);
	// Active fingers between pointer events; deliberately not reactive, nothing renders from it.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const pointers = new Map<number, { x: number; y: number }>();

	const colorVars: Record<keyof MapColors, string> = {
		background: '--map-bg',
		lawn: '--map-lawn',
		border: '--map-border',
		exclusion: '--map-exclusion',
		dock: '--map-dock',
		way: '--map-way',
		wayDone: '--map-way-done',
		trail: '--map-trail',
		target: '--map-target',
		robot: '--map-robot',
		robotOutline: '--map-robot-outline'
	};

	function colors(): MapColors {
		const style = getComputedStyle(canvas);
		const c = {} as MapColors;
		for (const [key, cssVar] of Object.entries(colorVars) as [keyof MapColors, string][]) {
			c[key] = style.getPropertyValue(cssVar).trim() || '#888';
		}
		return c;
	}

	function refit() {
		vp = fit(mapPoints(layers), vp.width, vp.height);
		userMoved = false;
	}

	// Follow the data until the user pans or zooms. Only new data triggers this;
	// reading vp untracked keeps the effect from re-running on its own write.
	$effect(() => {
		const points = mapPoints(layers);
		untrack(() => {
			if (!userMoved && points.length > 0) {
				vp = fit(points, vp.width, vp.height);
			}
		});
	});

	$effect(() => {
		const ctx = canvas?.getContext('2d');
		if (!ctx) return; // e.g. jsdom in tests
		const dpr = window.devicePixelRatio || 1;
		canvas.width = Math.round(vp.width * dpr);
		canvas.height = Math.round(vp.height * dpr);
		ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
		drawMap(ctx, vp, layers, colors());
	});

	onMount(() => {
		const observer = new ResizeObserver(([entry]) => {
			const { width, height } = entry.contentRect;
			vp = userMoved ? resize(vp, width, height) : fit(mapPoints(layers), width, height);
		});
		observer.observe(canvas);
		return () => observer.disconnect();
	});

	function onWheel(e: WheelEvent) {
		e.preventDefault();
		userMoved = true;
		vp = zoomAt(vp, Math.exp(-e.deltaY * 0.002), { x: e.offsetX, y: e.offsetY });
	}

	function onPointerDown(e: PointerEvent) {
		canvas.setPointerCapture?.(e.pointerId);
		pointers.set(e.pointerId, { x: e.offsetX, y: e.offsetY });
	}

	function onPointerMove(e: PointerEvent) {
		const prev = pointers.get(e.pointerId);
		if (!prev) return;
		const next = { x: e.offsetX, y: e.offsetY };
		userMoved = true;
		if (pointers.size === 1) {
			vp = pan(vp, next.x - prev.x, next.y - prev.y);
		} else if (pointers.size === 2) {
			// pinch: zoom by the change of distance between both fingers
			const other = [...pointers.entries()].find(([id]) => id !== e.pointerId)![1];
			const before = Math.hypot(prev.x - other.x, prev.y - other.y);
			const after = Math.hypot(next.x - other.x, next.y - other.y);
			if (before > 0) {
				vp = zoomAt(vp, after / before, { x: (next.x + other.x) / 2, y: (next.y + other.y) / 2 });
			}
		}
		pointers.set(e.pointerId, next);
	}

	function onPointerUp(e: PointerEvent) {
		pointers.delete(e.pointerId);
	}
</script>

<div class="map">
	<canvas
		bind:this={canvas}
		aria-label={label}
		onwheel={onWheel}
		onpointerdown={onPointerDown}
		onpointermove={onPointerMove}
		onpointerup={onPointerUp}
		onpointercancel={onPointerUp}
	></canvas>
	{#if userMoved}
		<button class="fit" type="button" onclick={refit}>Fit</button>
	{/if}
</div>

<style>
	.map {
		position: relative;
		width: 100%;
		height: 100%;
		min-height: 240px;
	}
	canvas {
		display: block;
		width: 100%;
		height: 100%;
		touch-action: none;
		border-radius: 12px;
	}
	.fit {
		position: absolute;
		top: 8px;
		right: 8px;
	}
</style>
