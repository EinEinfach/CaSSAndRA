<!-- Test helper: provides a stream (if given) and reads it back with useStream. -->
<script lang="ts">
	import type { EventStream } from '#shared/events.ts';
	import { provideStream, useStream } from '#shared/streamContext.ts';

	let { stream }: { stream?: EventStream } = $props();
	// svelte-ignore state_referenced_locally
	if (stream) provideStream(stream);
	const used = useStream();

	export function got() {
		return used;
	}
</script>
