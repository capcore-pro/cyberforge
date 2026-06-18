import { readFileSync } from "node:fs";
import { join } from "node:path";
import { app } from "electron";

/** Version applicative — lue depuis app.asar/package.json (fiable en packagé). */
export function getAppVersion(): string {
  try {
    const pkgPath = join(app.getAppPath(), "package.json");
    const pkg = JSON.parse(readFileSync(pkgPath, "utf-8")) as { version?: string };
    return pkg.version ?? app.getVersion();
  } catch {
    return app.getVersion();
  }
}
