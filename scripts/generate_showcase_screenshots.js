const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = process.cwd();
const ASSETS_DIR = path.join(ROOT, "docs", "assets");
const SHOWCASE_DIR = path.join(ROOT, "docs", "showcase");

const LOG_PATH = path.join(SHOWCASE_DIR, "showcase.log");
const EVIDENCE_PATH = path.join(SHOWCASE_DIR, "evidence.html");
const EVIDENCE_LIGHT_PATH = path.join(SHOWCASE_DIR, "evidence-light.html");

const TERMINAL_OUT = path.join(ASSETS_DIR, "showcase-terminal.png");
const EVIDENCE_OUT = path.join(ASSETS_DIR, "showcase-evidence.png");
const EVIDENCE_LIGHT_OUT = path.join(ASSETS_DIR, "showcase-evidence-light.png");

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function buildTerminalHtml(logText) {
  const rawLines = logText.trimEnd().split(/\r?\n/);
  const maxLines = 80;
  let lines = rawLines;
  if (rawLines.length > maxLines) {
    const head = rawLines.slice(0, 28);
    const tail = rawLines.slice(-48);
    lines = [...head, "", "··· snip ···", "", ...tail];
  }

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>AgentGate Showcase</title>
  <style>
    :root {
      --bg: #0c1412;
      --bg-2: #101b18;
      --frame: #121f1c;
      --frame-border: rgba(148, 163, 184, 0.15);
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #0e7c7b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "SF Pro Display", "Inter", system-ui, sans-serif;
      background:
        radial-gradient(circle at 10% 20%, rgba(14, 124, 123, 0.25), transparent 45%),
        radial-gradient(circle at 90% 10%, rgba(242, 166, 90, 0.2), transparent 40%),
        linear-gradient(180deg, var(--bg), var(--bg-2));
      color: var(--text);
      display: grid;
      place-items: center;
      min-height: 100vh;
      padding: 48px;
    }
    .terminal {
      width: 1200px;
      background: var(--frame);
      border-radius: 18px;
      border: 1px solid var(--frame-border);
      box-shadow: 0 40px 100px rgba(0, 0, 0, 0.5);
      overflow: hidden;
    }
    .titlebar {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 18px;
      border-bottom: 1px solid var(--frame-border);
      background: rgba(15, 23, 42, 0.6);
    }
    .dot {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      display: inline-block;
    }
    .dot.red { background: #f87171; }
    .dot.yellow { background: #facc15; }
    .dot.green { background: #4ade80; }
    .title {
      margin-left: 8px;
      color: var(--muted);
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    pre {
      margin: 0;
      padding: 24px 28px 32px;
      font-family: "JetBrains Mono", "SFMono-Regular", Menlo, Monaco, monospace;
      font-size: 14px;
      line-height: 1.45;
      color: var(--text);
      white-space: pre-wrap;
    }
    .accent {
      color: var(--accent);
      font-weight: 600;
    }
  </style>
</head>
<body>
  <div class="terminal">
    <div class="titlebar">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
      <span class="title">AgentGate Showcase</span>
    </div>
    <pre>${escapeHtml(lines.join("\n"))}</pre>
  </div>
</body>
</html>`;
}

async function screenshotTerminal(page) {
  if (!fs.existsSync(LOG_PATH)) {
    throw new Error(`Missing ${LOG_PATH}. Run make showcase first.`);
  }
  const logText = fs.readFileSync(LOG_PATH, "utf8");
  const html = buildTerminalHtml(logText);
  await page.setViewportSize({ width: 1400, height: 900 });
  await page.setContent(html, { waitUntil: "networkidle" });
  await page.screenshot({ path: TERMINAL_OUT });
}

async function screenshotEvidence(page, inputPath, outputPath) {
  if (!fs.existsSync(inputPath)) {
    return;
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`file://${inputPath}`, { waitUntil: "networkidle" });
  await page.waitForTimeout(300);
  await page.screenshot({ path: outputPath });
}

async function main() {
  fs.mkdirSync(ASSETS_DIR, { recursive: true });

  const browser = await chromium.launch();
  const context = await browser.newContext({ deviceScaleFactor: 2 });
  const page = await context.newPage();

  await screenshotTerminal(page);
  await screenshotEvidence(page, EVIDENCE_PATH, EVIDENCE_OUT);
  await screenshotEvidence(page, EVIDENCE_LIGHT_PATH, EVIDENCE_LIGHT_OUT);

  await browser.close();
  console.log("Screenshots written to docs/assets.");
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
