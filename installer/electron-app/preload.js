/**
 * Preload script — runs in a sandboxed renderer context.
 *
 * We intentionally keep this minimal.  The app communicates with the
 * backend entirely via HTTP (fetch / axios), so no Node APIs are
 * exposed to the renderer.
 */

const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  platform: process.platform,
});
