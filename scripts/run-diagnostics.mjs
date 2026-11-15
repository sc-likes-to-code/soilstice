// Runs backend/scripts/diagnose_environment.py using backend virtualenv's Python.
import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";

const py = ["backend/.venv/Scripts/python.exe", "backend/.venv/bin/python", "python3", "python"].find((p) => existsSync(p));
if (!py) {
  console.error("Python environment not found; see backend/README.md");
  process.exit(1);
}

const r = spawnSync(py, ["backend/scripts/diagnose_environment.py", ...process.argv.slice(2)], {
  stdio: "inherit",
  env: { ...process.env },
});

process.exit(r.status ?? 1);
