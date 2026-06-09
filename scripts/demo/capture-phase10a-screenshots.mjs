#!/usr/bin/env node
/**
 * Phase 10A — capture real dashboard screenshots via Playwright/Chromium.
 * Requires core profile running and live telemetry warm-up.
 */
import { chromium } from "playwright";
import { execSync } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, "../..");
const DASHBOARD_URL = process.env.DASHBOARD_URL || "http://localhost:3000";
const API_BASE = process.env.API_BASE || "http://localhost:8000";
const WARMUP_MS = Number(process.env.SCREENSHOT_WARMUP_MS || 30000);
const TIMESTAMP = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
const OUT_DIR = join(ROOT, "docs/evidence/phase10/demo/screenshots", TIMESTAMP);
const LATEST_DIR = join(ROOT, "docs/evidence/phase10/demo/screenshots/latest");

function git(cmd) {
  try {
    return execSync(`git -C "${ROOT}" ${cmd}`, { encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

function dockerProfiles() {
  try {
    const ps = execSync("docker compose --profile core ps --format json", {
      encoding: "utf8",
      cwd: ROOT,
    });
    const running = ps
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .filter((c) => c.State === "running")
      .map((c) => c.Service);
    return running.length ? `core (${running.join(", ")})` : "core (not running)";
  } catch {
    return "core (unknown)";
  }
}

const SHOTS = [
  {
    file: "00_dashboard_overview.png",
    testId: "connection-status",
    label: "Dashboard overview / connection status",
    fullPage: false,
  },
  {
    file: "01_live_telemetry_streams.png",
    testId: "live-telemetry",
    label: "Live telemetry streams",
    waitFor: "#event-counter",
    minEvents: 5,
  },
  {
    file: "02_edge_inference_and_fusion.png",
    testId: "edge-inference",
    label: "Edge inference / model scores",
    waitFor: "#model-score-counter",
    minEvents: 3,
  },
  {
    file: "03_agent_traces_and_hitl.png",
    testId: "agent-traces",
    label: "Agent traces and HITL context",
    before: async (page) => {
      await page.locator('[data-testid="agent-traces"]').scrollIntoViewIfNeeded();
    },
  },
  {
    file: "04_digital_twin_state_mirror.png",
    testId: "digital-twin",
    label: "Digital twin state mirror",
  },
  {
    file: "05_evidence_center_or_observability.png",
    testId: "operational-status",
    label: "Operational status / evidence observability",
    extra: async (page) => {
      await page.locator('[data-testid="mission-control"]').scrollIntoViewIfNeeded();
    },
  },
  {
    file: "06_failure_or_degraded_mode_if_available.png",
    testId: "failure-injection",
    label: "Failure injection (simulated degraded mode)",
    before: async (page) => {
      const btn = page.locator('button[data-scenario="sensor_dropout"]');
      if (await btn.isVisible()) {
        await btn.click();
        await page.waitForTimeout(2000);
      }
    },
  },
  {
    file: "07_ros2_nav_slam_compose_status_if_available.png",
    testId: "nav-slam",
    label: "ROS2 Nav2/SLAM MiniLab (compose-validated; offline in core-only)",
  },
];

async function waitForCounter(page, selector, min) {
  const deadline = Date.now() + WARMUP_MS;
  while (Date.now() < deadline) {
    const text = await page.locator(selector).textContent();
    const n = Number.parseInt(text || "0", 10);
    if (n >= min) return n;
    await page.waitForTimeout(1000);
  }
  throw new Error(`Timeout waiting for ${selector} >= ${min}`);
}

async function copyLatest(srcDir) {
  mkdirSync(LATEST_DIR, { recursive: true });
  for (const shot of SHOTS) {
    execSync(`cp "${join(srcDir, shot.file)}" "${join(LATEST_DIR, shot.file)}"`);
  }
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();

  const results = [];
  let failed = false;

  try {
    await page.goto(DASHBOARD_URL, { waitUntil: "networkidle", timeout: 60000 });
    await page.waitForSelector('[data-testid="connection-status"]', { timeout: 30000 });

    // Warm-up: wait for live sensor + model score traffic
    try {
      await waitForCounter(page, "#event-counter", 5);
      await waitForCounter(page, "#model-score-counter", 3);
    } catch (err) {
      console.warn("Warm-up warning:", err.message);
      results.push({ note: `warm-up partial: ${err.message}` });
    }

    for (const shot of SHOTS) {
      const dest = join(OUT_DIR, shot.file);
      try {
        if (shot.before) await shot.before(page);
        const section = page.locator(`[data-testid="${shot.testId}"]`);
        await section.scrollIntoViewIfNeeded();
        await page.waitForTimeout(500);
        if (shot.waitFor && shot.minEvents) {
          await waitForCounter(page, shot.waitFor, shot.minEvents);
        }
        if (shot.extra) await shot.extra(page);

        if (shot.fullPage === false) {
          await section.screenshot({ path: dest });
        } else {
          await page.screenshot({ path: dest, fullPage: true });
        }
        results.push({ file: shot.file, status: "ok", label: shot.label });
        console.log(`Captured ${shot.file}`);
      } catch (err) {
        failed = true;
        results.push({ file: shot.file, status: "fail", error: err.message });
        console.error(`Failed ${shot.file}:`, err.message);
      }
    }
  } finally {
    await browser.close();
  }

  const metadata = {
    timestamp: TIMESTAMP,
    git_sha: git("rev-parse HEAD"),
    branch: git("branch --show-current"),
    command: "cd scripts/demo && npm run capture",
    dashboard_url: DASHBOARD_URL,
    api_base: API_BASE,
    docker_profiles: dockerProfiles(),
    warmup_ms: WARMUP_MS,
    screenshots: results,
    pass: !failed,
    notes: [
      "ROS2/Nav2/SLAM panel shows offline state under core-only profile — compose-validated, not live-gated.",
      "Screenshots are from real local execution; no generated or stock imagery.",
    ],
  };

  writeFileSync(join(OUT_DIR, "capture-metadata.json"), JSON.stringify(metadata, null, 2));
  copyLatest(OUT_DIR);

  console.log(`\nScreenshots saved to ${OUT_DIR}`);
  console.log(`Latest symlink copies in ${LATEST_DIR}`);

  if (failed) process.exit(1);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
