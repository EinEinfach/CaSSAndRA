import { defineConfig } from 'vitest/config';
import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { svelteTesting } from '@testing-library/svelte/vite';

// Backend for `npm run dev` (make dev starts it on this port).
const backend = process.env.CASSANDRA_BACKEND ?? 'http://127.0.0.1:8050';

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			// Pure SPA: the Go server serves index.html for every client route.
			adapter: adapter({ fallback: 'index.html' })
		}),
		svelteTesting()
	],
	server: {
		proxy: { '/api': { target: backend, ws: true } }
	},
	test: {
		expect: { requireAssertions: true },
		include: ['tests/**/*.test.ts'],
		// jsdom for component tests; plain logic tests run fine in it too.
		environment: 'jsdom'
	}
});
