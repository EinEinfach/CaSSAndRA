<script lang="ts">
	import { onDestroy } from 'svelte';
	import { move } from './api.ts';
	import { MoveSender, driveFromOffset, type Drive } from './drive.ts';

	let {
		disabled = false,
		sender = new MoveSender((d: Drive) => move(d.linear, d.angular))
	}: { disabled?: boolean; sender?: MoveSender } = $props();

	const size = 160;
	const radius = size / 2 - 20;
	let knob = $state({ x: 0, y: 0 });
	let pointerId: number | null = null;
	let pad: HTMLDivElement;

	function offset(e: PointerEvent) {
		const r = pad.getBoundingClientRect();
		let dx = e.clientX - (r.left + r.width / 2);
		let dy = e.clientY - (r.top + r.height / 2);
		const len = Math.hypot(dx, dy);
		if (len > radius) {
			dx = (dx / len) * radius;
			dy = (dy / len) * radius;
		}
		return { dx, dy };
	}

	function down(e: PointerEvent) {
		if (disabled || pointerId !== null) return;
		pointerId = e.pointerId;
		pad.setPointerCapture?.(e.pointerId);
		drag(e);
	}

	function drag(e: PointerEvent) {
		if (e.pointerId !== pointerId) return;
		const { dx, dy } = offset(e);
		knob = { x: dx, y: dy };
		sender.update(driveFromOffset(dx, dy, radius));
	}

	function up(e: PointerEvent) {
		if (e.pointerId !== pointerId) return;
		pointerId = null;
		knob = { x: 0, y: 0 };
		sender.release();
	}

	// Never leave the robot driving when the component goes away.
	onDestroy(() => sender.release());
</script>

<div
	bind:this={pad}
	class="pad"
	class:disabled
	style:width="{size}px"
	style:height="{size}px"
	role="slider"
	aria-label="Joystick: drag up to drive forward, sideways to turn"
	aria-valuenow={Math.round(-knob.y)}
	aria-disabled={disabled}
	tabindex="-1"
	onpointerdown={down}
	onpointermove={drag}
	onpointerup={up}
	onpointercancel={up}
	onlostpointercapture={up}
>
	<div class="knob" style:transform="translate({knob.x}px, {knob.y}px)"></div>
</div>

<style>
	.pad {
		position: relative;
		border-radius: 50%;
		background: var(--surface-sunken);
		border: 2px solid var(--border);
		touch-action: none;
		user-select: none;
		display: grid;
		place-items: center;
	}
	.disabled {
		opacity: 0.4;
	}
	.knob {
		width: 112px;
		height: 112px;
		border-radius: 50%;
		background: var(--accent);
		box-shadow: 0 2px 6px rgb(0 0 0 / 0.3);
		pointer-events: none;
	}
</style>
