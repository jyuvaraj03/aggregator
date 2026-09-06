import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { writeFile } from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";
import { format, resolveConfig } from "prettier";

// Export directly from FastAPI; no running server or database migrations are needed.
const schema = execFileSync(
    "uv",
    [
        "run",
        "python",
        "-c",
        "import json; from aggregator.api.app import app; print(json.dumps(app.openapi()))",
    ],
    { cwd: fileURLToPath(new URL("../../", import.meta.url)), encoding: "utf8" },
);
const types = await openapiTS(JSON.parse(schema));
const output = new URL("../src/lib/api/schema.d.ts", import.meta.url);
await writeFile(
    output,
    await format(astToString(types), {
        ...(await resolveConfig(fileURLToPath(output))),
        parser: "typescript",
    }),
);
