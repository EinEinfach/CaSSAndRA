import { defineConfig } from '@playwright/test';

const port = 4173;

// E2E runs against the real Go binary with the embedded frontend, a fresh
// data directory (never ~/.cassandra) and the simulated robot. The tests share
// that robot, so they run one after another.
export default defineConfig({
	testDir: 'tests/e2e',
	testMatch: '**/*.e2e.ts',
	workers: 1,
	use: { baseURL: `http://127.0.0.1:${port}` },
	webServer: {
		command: `make -C .. build && rm -rf ../.e2e-data && ../bin/cassandra --host 127.0.0.1 --port ${port} --data-dir ../.e2e-data`,
		url: `http://127.0.0.1:${port}/api/health`,
		reuseExistingServer: !process.env.CI,
		timeout: 180_000
	}
});
