// One event stream for the whole app: the layout provides it, pages use it.
import { getContext, setContext } from 'svelte';
import type { EventStream } from './events.ts';

const key = Symbol('event stream');

export function provideStream(stream: EventStream): void {
	setContext(key, stream);
}

export function useStream(): EventStream {
	const stream = getContext<EventStream | undefined>(key);
	if (!stream) {
		throw new Error('no event stream: useStream must be called below the layout');
	}
	return stream;
}
