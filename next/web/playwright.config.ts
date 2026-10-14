import { defineConfig } from '@playwright/test';

const port = 4173;

// E2E runs against the real Go binary with the embedded frontend.
export default defineConfig({
	testDir: 'tests/e2e',
	testMatch: '**/*.e2e.ts',
	use: { baseURL: `http://127.0.0.1:${port}` },
	webServer: {
		command: `make -C .. build && ../bin/cassandra --host 127.0.0.1 --port ${port}`,
		url: `http://127.0.0.1:${port}/api/health`,
		reuseExistingServer: !process.env.CI,
		timeout: 180_000
	}
});
