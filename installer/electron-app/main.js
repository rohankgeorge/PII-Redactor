/**
 * Electron main process for PII Redactor.
 *
 * Responsibilities:
 *   1. Spawn the bundled Python/FastAPI backend as a child process.
 *   2. Poll the health endpoint until the server is ready.
 *   3. Open the UI in a BrowserWindow pointing at the backend.
 *   4. Kill the backend when the user quits.
 */

const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");
const http = require("http");

const BACKEND_PORT = 8000;
const BACKEND_URL = `http://localhost:${BACKEND_PORT}`;
const HEALTH_URL = `${BACKEND_URL}/api/`;
const MAX_WAIT_MS = 60_000; // 60 seconds to wait for backend
const POLL_INTERVAL_MS = 500;

let backendProcess = null;
let mainWindow = null;

/**
 * Resolve the path to the backend executable.
 * In a packaged app the backend dist lives next to the Electron asar.
 */
function getBackendPath() {
  const isPackaged = app.isPackaged;
  if (isPackaged) {
    // When packaged, backend is alongside the app resources
    const resourcesDir = process.resourcesPath;
    const exeName = process.platform === "win32" ? "server.exe" : "server";
    return path.join(resourcesDir, "backend_dist", exeName);
  }
  // Development fallback — assume backend is already running
  return null;
}

/**
 * Launch the backend subprocess.
 */
function startBackend() {
  const backendPath = getBackendPath();
  if (!backendPath) {
    console.log("Development mode — assuming backend is already running.");
    return;
  }

  console.log(`Starting backend: ${backendPath}`);
  backendProcess = spawn(backendPath, [], {
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, CORS_ORIGINS: "*" },
  });

  backendProcess.stdout.on("data", (data) => {
    console.log(`[backend] ${data.toString().trim()}`);
  });

  backendProcess.stderr.on("data", (data) => {
    console.error(`[backend:err] ${data.toString().trim()}`);
  });

  backendProcess.on("exit", (code) => {
    console.log(`Backend exited with code ${code}`);
    backendProcess = null;
  });
}

/**
 * Poll the backend health endpoint until it responds.
 */
function waitForBackend() {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    function poll() {
      const req = http.get(HEALTH_URL, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else {
          schedulePoll();
        }
        res.resume();
      });

      req.on("error", () => {
        schedulePoll();
      });

      req.setTimeout(2000, () => {
        req.destroy();
        schedulePoll();
      });
    }

    function schedulePoll() {
      if (Date.now() - start > MAX_WAIT_MS) {
        reject(new Error("Backend did not start in time"));
        return;
      }
      setTimeout(poll, POLL_INTERVAL_MS);
    }

    poll();
  });
}

/**
 * Create the main application window.
 */
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: "PII Redactor",
    icon: path.join(__dirname, "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL(BACKEND_URL);

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

/**
 * Kill the backend process tree.
 */
function stopBackend() {
  if (!backendProcess) return;
  try {
    if (process.platform === "win32") {
      // On Windows, kill the entire process tree
      spawn("taskkill", ["/pid", String(backendProcess.pid), "/f", "/t"]);
    } else {
      backendProcess.kill("SIGTERM");
    }
  } catch (err) {
    console.error("Error stopping backend:", err.message);
  }
  backendProcess = null;
}

// ── App lifecycle ──────────────────────────────────────────

app.on("ready", async () => {
  startBackend();

  try {
    await waitForBackend();
  } catch (err) {
    dialog.showErrorBox(
      "Startup Error",
      "The PII Redactor backend failed to start.\n\n" + err.message,
    );
    app.quit();
    return;
  }

  createWindow();
});

app.on("window-all-closed", () => {
  stopBackend();
  app.quit();
});

app.on("before-quit", () => {
  stopBackend();
});
