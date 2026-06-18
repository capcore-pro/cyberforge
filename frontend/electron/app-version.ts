import { app } from "electron";

/** Version applicative — synchronisée avec `package.json` via Electron. */
export function getAppVersion(): string {
  return app.getVersion();
}
