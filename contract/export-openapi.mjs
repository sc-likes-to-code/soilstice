// Exports backend/openapi.json using the backend virtualenv's Python (Windows or POSIX layout).
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
const py = ["backend/.venv/Scripts/python.exe", "backend/.venv/bin/python"].find((p) => existsSync(p));
if (!py) { console.error("backend/.venv not found; see backend/README.md"); process.exit(1); }
const r = spawnSync(py, ["backend/scripts/export_openapi.py", ...process.argv.slice(2)], {
  stdio: "inherit", env: { ...process.env, SOILSTICE_LOG_LEVEL: "WARNING" },
});
process.exit(r.status ?? 1);
