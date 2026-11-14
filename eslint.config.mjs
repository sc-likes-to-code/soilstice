import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // UI_ARCHITECTURE §1.4: only the service factory may import mock implementations.
  {
    files: ["src/**/*.{ts,tsx}"],
    ignores: ["src/services/index.ts", "src/services/mock/**", "src/**/*.test.ts"],
    rules: {
      "no-restricted-imports": [
        "error",
        {
          patterns: [
            { group: ["@/services/mock", "@/services/mock/*", "**/services/mock/**", "./mock/*"], message: "Import services through '@/services' (getServices). Mock implementations are only reachable via the factory." },
          ],
        },
      ],
    },
  },
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
