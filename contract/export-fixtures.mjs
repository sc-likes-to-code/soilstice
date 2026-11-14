// Runs the env-gated vitest exporter so mock-service fixtures land in backend/tests/fixtures/frontend_mock.
import { spawnSync } from "node:child_process";
const r = spawnSync("npx", ["vitest", "run", "src/services/mock/export-fixtures.test.ts"], {
  stdio: "inherit", shell: true, env: { ...process.env, EXPORT_FIXTURES_DIR: "backend/tests/fixtures/frontend_mock" },
});
process.exit(r.status ?? 1);
