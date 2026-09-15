// Boundary SDK capture shim (500-line budget, this file is ~60).
// Usage: import "boundary-sdk/capture" once at app startup, then run the app
// via `boundary dev -- <cmd>`. When BOUNDARY_CAPTURE=1 it wraps global fetch
const net = require("node:net");

const sock = process.env.BOUNDARY_SOCKET;
const enabled = process.env.BOUNDARY_CAPTURE === "1" && sock && !globalThis.__boundary_patched;

function send(frame) {
  try {
    const line = JSON.stringify(frame).slice(0, 8000) + "\n";
    const c = net.createConnection(sock);
    c.on("error", () => {});
    c.end(line);
  } catch {}
}

if (enabled && typeof globalThis.fetch === "function") {
  globalThis.__boundary_patched = true;
  const orig = globalThis.fetch.bind(globalThis);
  globalThis.fetch = async (...args) => {
    const res = await orig(...args);
    try {
      const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "unknown-url";
      const clone = res.clone();
      const data = await clone.json().catch(() => null);
      if (data !== null && typeof data === "object") {
        const sample = Array.isArray(data) ? data.slice(0, 3) : data;
        send({ endpoint: hostOf(url), sample });
      }
    } catch {}
    return res;
  };
}

function hostOf(url) {
  try {
    const u = new URL(url, "http://local");
    return (u.hostname + u.pathname).replace(/^local\//, "/").slice(0, 160);
  } catch {
    return String(url).slice(0, 160);
  }
}
