import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import path from "node:path";


const releaseId = (process.env.KWBL_PUBLIC_RELEASE_ID || "").trim();
if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$/.test(releaseId) || releaseId === "unpublished") {
  console.error("Set KWBL_PUBLIC_RELEASE_ID to a validated immutable R2 release before deploying.");
  process.exit(2);
}

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const executable = process.platform === "win32" ? "wrangler.cmd" : "wrangler";
const wrangler = path.resolve(scriptDirectory, "../node_modules/.bin", executable);
const result = spawnSync(
  wrangler,
  ["deploy", "--var", `PUBLIC_RELEASE_ID:${releaseId}`],
  { stdio: "inherit" },
);

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
