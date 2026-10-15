<script lang="ts" module>
	import type { Point } from './viewport.ts';

	/** Pointer handling for editors, in world coordinates (meters). */
	export interface MapInteraction {
		/** A short click or tap without dragging. */
		tap?(world: Point, metersPerPixel: number): void;
		/** Pointer pressed; return true to drag (move/up follow) instead of panning. */
		press?(world: Point, metersPerPixel: number): boolean;
		move?(world: Point): void;
		release?(): void;
	}
</script>

<script lang="ts">
	import { onMount, untrack } from 'svelte';
	import { drawMap, mapPoints, type MapColors, type MapLayers } from './drawMap.ts';
	import { fit, pan, resize, toWorld, zoomAt, type Viewport } from './viewport.ts';

	interface Props {
		layers: MapLayers;
		label?: string;
		/**
		 * "always" follows the data until the user moves the view; "once" fits what
		 * is there when the canvas appears and then stays, e.g. while editing.
		 */
		fitMode?: 'always' | 'once';
		interact?: MapInteraction;
	}
	let { layers, label = 'Map', fitMode = 'always', interact }: Props = $props();

	/** Pointer travel in pixels below which a press counts as a tap. */
	const TAP_SLOP = 6;

	let canvas: HTMLCanvasElement;
	let vp = $state<Viewport>(fit([], 300, 300));
	let userMoved = $state(false);
	// fitMode "once": the points the view was fitted to; null until then.
	let fitBase: Point[] | null = null;
	// Pointer bookkeeping between events; deliberately not reactive, nothing renders from it.
	// eslint-disable-next-line svelte/prefer-svelte-reactivity
	const pointers = new Map<number, { x: number; y: number }>();
	let press: {
		id: number;
		start: { x: number; y: number };
		dragging: boolean;
		moved: boolean;
	} | null = null;

	const colorVars: Record<keyof MapColors, string> = {
		background: '--map-bg',
		lawn: '--map-lawn',
		border: '--map-border',
		exclusion: '--map-exclusion',
		dock: '--map-dock',
		wire: '--map-wire',
		way: '--map-way',
		wayDone: '--map-way-done',
		trail: '--map-trail',
		target: '--map-target',
		robot: '--map-robot',
		robotOutline: '--map-robot-outline',
		handle: '--map-handle',
		handleFill: '--map-handle-fill'
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
			if (fitMode === 'once') {
				if (fitBase === null) {
					fitBase = points;
					vp = fit(points, vp.width, vp.height);
				}
				return;
			}
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
			if (userMoved) vp = resize(vp, width, height);
			else vp = fit(fitMode === 'once' ? (fitBase ?? []) : mapPoints(layers), width, height);
		});
		observer.observe(canvas);
		return () => observer.disconnect();
	});

	/** Position in canvas pixels; works without layout (offsetX is not set in tests). */
	function local(e: MouseEvent) {
		const r = canvas.getBoundingClientRect();
		return { x: e.clientX - r.left, y: e.clientY - r.top };
	}

	function onWheel(e: WheelEvent) {
		e.preventDefault();
		userMoved = true;
		vp = zoomAt(vp, Math.exp(-e.deltaY * 0.002), local(e));
	}

	function onPointerDown(e: PointerEvent) {
		canvas.setPointerCapture?.(e.pointerId);
		const at = local(e);
		pointers.set(e.pointerId, at);
		if (pointers.size === 1) {
			const dragging = interact?.press?.(toWorld(vp, at), 1 / vp.scale) ?? false;
			press = { id: e.pointerId, start: at, dragging, moved: false };
		} else {
			press = null; // a second finger: pinch, never a tap or drag
		}
	}

	function onPointerMove(e: PointerEvent) {
		const prev = pointers.get(e.pointerId);
		if (!prev) return;
		const next = local(e);
		if (press?.id === e.pointerId && !press.moved) {
			press.moved = Math.hypot(next.x - press.start.x, next.y - press.start.y) > TAP_SLOP;
		}
		if (press?.dragging && press.id === e.pointerId) {
			interact?.move?.(toWorld(vp, next));
		} else if (pointers.size === 1) {
			userMoved = true;
			vp = pan(vp, next.x - prev.x, next.y - prev.y);
		} else if (pointers.size === 2) {
			// pinch: zoom by the change of distance between both fingers
			userMoved = true;
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
		if (press?.id !== e.pointerId) return;
		if (press.dragging) {
			interact?.release?.();
		} else if (!press.moved && e.type === 'pointerup') {
			interact?.tap?.(toWorld(vp, local(e)), 1 / vp.scale);
		}
		press = null;
	}
</script>

<div class="map">
	<canvas
		bind:this={canvas}
		aria-label={label}
		class:editing={!!interact}
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
	/* Absolute, so the drawing buffer size never feeds back into the layout. */
	canvas {
		position: absolute;
		inset: 0;
		display: block;
		width: 100%;
		height: 100%;
		touch-action: none;
		border-radius: 16px;
	}
	canvas.editing {
		cursor: crosshair;
	}
	.fit {
		position: absolute;
		top: 8px;
		right: 8px;
	}
</style>
