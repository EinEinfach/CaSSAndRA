import { render } from '@testing-library/svelte';
import { describe, expect, it } from 'vitest';
import StreamHarness from './StreamHarness.svelte';
import { EventStream, type EventSourceLike } from '#shared/events.ts';

const fakeSource = (): EventSourceLike => ({
	onopen: null,
	onerror: null,
	addEventListener() {},
	removeEventListener() {},
	close() {}
});

describe('streamContext', () => {
	it('gives children the stream of their parent', () => {
		const stream = new EventStream('/x', fakeSource);
		const { component } = render(StreamHarness, { stream });
		expect(component.got()).toBe(stream);
	});

	it('fails clearly without a provider', () => {
		expect(() => render(StreamHarness, {})).toThrow('no event stream');
	});
});
