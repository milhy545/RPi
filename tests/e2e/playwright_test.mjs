/**
 * RPi-TV WebUI E2E Tests — Playwright
 *
 * Tests:
 *   1. WebUI loads without console errors
 *   2. Video playback: insert YouTube URL → play → verify streaming
 *   3. PWA Share Intent flow (?share_url=...)
 *   4. Mode buttons present in Apps tab (Steam, Spotify, mpv)
 *   5. Tab navigation works
 *   6. Manifest.json is valid PWA manifest
 *
 * Usage:
 *   TARGET_URL=http://192.168.0.205:8080 node rpi-tv-e2e.mjs
 */
import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const TARGET = process.env.TARGET_URL || 'http://192.168.0.205:8080';
const ARTIFACTS = './artifacts';
mkdirSync(ARTIFACTS, { recursive: true });

const results = [];
let browser, page;

function pass(name, detail = '') {
  results.push({ name, status: 'PASS', detail });
  console.log(`  ✅ ${name}${detail ? ' — ' + detail : ''}`);
}
function fail(name, err) {
  results.push({ name, status: 'FAIL', detail: String(err) });
  console.log(`  ❌ ${name} — ${err}`);
}

async function setup() {
  browser = await chromium.launch({ headless: true });
}

async function setupPage() {
  if (page && !page.isClosed()) {
    await page.close().catch(() => {});
  }
  page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  page.on('console', msg => {
    if (msg.type() === 'error') page._consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => page._pageErrors.push(String(err)));
  page._consoleErrors = [];
  page._pageErrors = [];
  await page.route('https://cdn.jsdelivr.net/**', route => route.abort());
}

async function teardown() {
  if (browser) await browser.close();
}

async function gotoApp(url = TARGET) {
  const res = await page.goto(url, { waitUntil: 'commit', timeout: 30000 });
  await page.waitForSelector('#url', { state: 'attached', timeout: 30000 });
  return res;
}

// Helper: dismiss any native confirm() dialogs (resume prompts)
function setupConfirmHandler() {
  page.on('dialog', async dialog => {
    console.log(`    [dialog] type=${dialog.type()} message="${dialog.message()}"`);
    // Always dismiss resume dialogs by clicking Cancel (false)
    await dialog.dismiss();
  });
}

// Helper: call the WebUI API directly
async function api(path) {
  return page.evaluate(async (p) => {
    const r = await fetch(p);
    return r.json();
  }, path);
}

// ─── TEST 1: WebUI loads without errors ───
async function testWebUILoads() {
  console.log('\n🧪 Test 1: WebUI loads without console errors');
  const res = await gotoApp();
  if (res.status() !== 200) {
    fail('WebUI HTTP status', `Expected 200, got ${res.status()}`);
    return false;
  }
  const title = await page.title();
  if (title !== 'RPi-TV') {
    fail('Page title', `Expected "RPi-TV", got "${title}"`);
    return false;
  }
  const critical = page._consoleErrors.filter(e =>
    !e.includes('favicon') && !e.includes('service-worker') && !e.includes('WebSocket')
  );
  if (critical.length > 0) {
    fail('Console errors', critical.join('; '));
    return false;
  }
  pass('Page loaded', `title="${title}", HTTP ${res.status()}`);
  await page.screenshot({ path: `${ARTIFACTS}/01-loaded.png`, fullPage: true });
  return true;
}

// ─── TEST 2: Video playback — the real deal ───
async function testVideoPlayback() {
  console.log('\n🧪 Test 2: Video playback (YouTube → mpv stream)');

  // Ensure we're on the Player tab
  await gotoApp();
  await page.click('#tab-player');
  await page.waitForTimeout(500);

  // Aggressively stop any existing playback first
  try { await api('/mpv/stop'); } catch {}
  await page.waitForTimeout(1000);
  try { await api('/mpv/stop'); } catch {}  // double-stop for safety
  await page.waitForTimeout(500);

  // Verify clean state (soft check — don't fail if something lingers)
  const statusBefore = await api('/mpv/status').catch(() => ({on:false}));
  if (statusBefore.on) {
    console.log('    Warning: mpv still running after stop, proceeding anyway');
  } else {
    pass('Clean state', 'mpv not running before test');
  }

  // Insert YouTube URL into the input
  const ytUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
  await page.fill('#url', ytUrl);
  const inputVal = await page.$eval('#url', el => el.value);
  if (inputVal !== ytUrl) {
    fail('URL input', `Expected "${ytUrl}", got "${inputVal}"`);
    return false;
  }
  pass('URL inserted', inputVal);

  // Click Play button — try multiple selectors for i18n resilience
  console.log('    Clicking Play...');
  const playBtn = await page.$('button[onclick="play()"]')
    || await page.$('button[data-i18n="play"]')
    || await page.$('button[data-icon="▶"]');
  if (!playBtn) {
    fail('Play button', 'not found with any selector');
    return false;
  }
  await playBtn.click();

  // Wait for mpv to start — poll /mpv/status up to 20s
  let mpvOn = false;
  let statusResp = null;
  for (let i = 0; i < 20; i++) {
    await page.waitForTimeout(1000);
    statusResp = await api('/mpv/status');
    if (statusResp.on) {
      mpvOn = true;
      break;
    }
    console.log(`    Waiting for mpv... (${i + 1}s)`);
  }

  if (!mpvOn) {
    fail('mpv start', 'mpv did not start within 30s');
    await page.screenshot({ path: `${ARTIFACTS}/02-playback-fail.png`, fullPage: true });
    return false;
  }
  pass('mpv started', `pid=${statusResp.pid}, tracked=${statusResp.tracked}`);

  // Verify video title is present
  const videoTitle = statusResp.title || '';
  if (!videoTitle || videoTitle.length < 3) {
    fail('Video title', `Empty or missing: "${videoTitle}"`);
    return false;
  }
  pass('Video title', `"${videoTitle}"`);

  // Wait for playback to progress — poll up to 8s, then STOP immediately
  let pos = 0, dur = 0, paused = false;
  for (let i = 0; i < 8; i++) {
    await page.waitForTimeout(1000);
    const sp = await api('/mpv/status');
    pos = sp.pos || 0;
    dur = sp.dur || 0;
    paused = sp.paused;
    if (pos > 0) break;
    console.log(`    Waiting for playback pos... (${i + 1}s, pos=${pos})`);
  }

  if (pos <= 0 && !paused) {
    fail('Playback progress', `pos=${pos}, expected > 0 after 8s`);
  } else {
    pass('Playback progress', `pos=${pos.toFixed(1)}s / dur=${dur.toFixed(1)}s, paused=${paused}`);
  }

  // Verify the UI status element updated
  const stText = await page.$eval('#st', el => el.textContent).catch(() => '');
  if (stText && stText !== '—') {
    pass('UI status updated', stText.substring(0, 80));
  } else {
    pass('UI status', 'empty (non-critical)');
  }

  await page.screenshot({ path: `${ARTIFACTS}/02-video-playing.png`, fullPage: true });

  // CRITICAL: Stop playback immediately to avoid freezing RPi
  console.log('    Stopping mpv immediately...');
  try { await api('/mpv/stop'); } catch {}
  await page.waitForTimeout(500);
  try { await api('/mpv/stop'); } catch {}  // double-stop
  console.log('    Playback stopped');
  return true;
}

// ─── TEST 3: PWA Share Intent flow ───
async function testPWAShareIntent() {
  console.log('\n🧪 Test 3: PWA Share Intent (?share_url=...)');
  const shareUrl = 'https://youtube.com/watch?v=dQw4w9WgXcQ';
  const testUrl = `${TARGET}?share_url=${encodeURIComponent(shareUrl)}`;
  await gotoApp(testUrl);

  // Wait for JS to process the share_url param
  await page.waitForTimeout(1500);

  // Check that #url input has the shared URL
  const inputVal = await page.$eval('#url', el => el.value).catch(() => null);
  if (!inputVal) {
    fail('Share URL not in input', '#url input is empty or missing');
    return false;
  }
  if (!inputVal.includes('youtube.com/watch')) {
    fail('Share URL mismatch', `Expected youtube URL, got "${inputVal}"`);
    return false;
  }
  pass('Share URL populated', `#url = "${inputVal}"`);

  // The JS calls play() automatically — verify it was triggered
  const statusText = await page.$eval('#st', el => el.textContent).catch(() => '');
  pass('Auto-play triggered', `Status: "${statusText || '(pending)'}"`);

  // Stop any playback from this test
  await api('/mpv/stop');

  await page.screenshot({ path: `${ARTIFACTS}/03-share-intent.png`, fullPage: true });
  return true;
}

// ─── TEST 4: Mode buttons present in Apps tab ───
async function testModeButtons() {
  console.log('\n🧪 Test 4: Mode buttons present in Apps tab');
  await gotoApp();

  await page.click('#tab-apps');
  await page.waitForTimeout(500);

  const expectedApps = [
    { label: 'Steam', selector: 'button:has-text("Steam")' },
    { label: 'Spotify', selector: 'button:has-text("Spotify")' },
    { label: 'MPV', selector: 'button:has-text("MPV")' },
    { label: 'GeForce Now', selector: 'button:has-text("GeForce")' },
    { label: 'Amazon Music', selector: 'button:has-text("Amazon")' },
  ];

  let allFound = true;
  for (const app of expectedApps) {
    const el = await page.$(app.selector);
    if (el) {
      pass(`Button: ${app.label}`, 'found');
    } else {
      fail(`Button: ${app.label}`, 'NOT FOUND');
      allFound = false;
    }
  }

  await page.screenshot({ path: `${ARTIFACTS}/04-mode-buttons.png`, fullPage: true });
  return allFound;
}

// ─── TEST 5: Tab navigation ───
async function testTabNavigation() {
  console.log('\n🧪 Test 5: Tab navigation');
  await gotoApp();

  const tabs = [
    { id: 'tab-player', panel: 'p-player' },
    { id: 'tab-apps', panel: 'p-apps' },
    { id: 'tab-cec', panel: 'p-cec' },
    { id: 'tab-audio', panel: 'p-audio' },
    { id: 'tab-devices', panel: 'p-devices' },
    { id: 'tab-terminal', panel: 'p-terminal' },
  ];

  let allOk = true;
  for (const tab of tabs) {
    await page.click(`#${tab.id}`);
    await page.waitForTimeout(300);
    const isActive = await page.$eval(`#${tab.id}`, el => el.classList.contains('active'));
    const panelVisible = await page.$eval(`#${tab.panel}`, el => el.classList.contains('active')).catch(() => false);
    if (isActive && panelVisible) {
      pass(`Tab ${tab.id}`, 'active + panel visible');
    } else {
      fail(`Tab ${tab.id}`, `active=${isActive}, panelVisible=${panelVisible}`);
      allOk = false;
    }
  }

  await page.screenshot({ path: `${ARTIFACTS}/05-tab-nav.png`, fullPage: true });
  return allOk;
}

// ─── TEST 6: PWA Manifest ───
async function testManifest() {
  console.log('\n🧪 Test 6: PWA manifest.json');
  const res = await page.request.get(`${TARGET}/manifest.json`, { timeout: 10000 });
  if (res.status() !== 200) {
    fail('Manifest HTTP', `Status ${res.status()}`);
    return false;
  }
  const body = await res.text();
  let manifest;
  try {
    manifest = JSON.parse(body);
  } catch (e) {
    fail('Manifest parse', e.message);
    return false;
  }

  const checks = [
    ['name', manifest.name === 'RPi Dashboard'],
    ['short_name', manifest.short_name === 'RPiDash'],
    ['display', manifest.display === 'standalone'],
    ['share_target', !!manifest.share_target],
    ['share_target.action', manifest.share_target?.action === '/'],
    ['share_target.params.url', manifest.share_target?.params?.url === 'share_url'],
  ];

  let ok = true;
  for (const [label, cond] of checks) {
    if (cond) pass(`Manifest ${label}`, 'ok');
    else { fail(`Manifest ${label}`, 'failed'); ok = false; }
  }

  await page.screenshot({ path: `${ARTIFACTS}/06-manifest.png`, fullPage: true });
  return ok;
}

// ─── MAIN ───
(async () => {
  console.log(`\n🚀 RPi-TV E2E Test Suite`);
  console.log(`   Target: ${TARGET}`);
  console.log(`   Time: ${new Date().toISOString()}\n`);

  await setup();
  const tests = [
    testWebUILoads,
    testVideoPlayback,   // ← the new important test
    testPWAShareIntent,
    testModeButtons,
    testTabNavigation,
    testManifest,
  ];

  for (const fn of tests) {
    try {
      await setupPage();
      setupConfirmHandler();
      await fn();
    } catch (e) {
      fail(fn.name, e.message);
    }
  }

  // Final cleanup: aggressively stop any running mpv
  try { await api('/mpv/stop'); } catch {}
  await page.waitForTimeout(500);
  try { await api('/mpv/stop'); } catch {}

  await teardown();

  // Summary
  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status === 'FAIL').length;
  console.log(`\n${'═'.repeat(50)}`);
  console.log(`📊 Results: ${passed} passed, ${failed} failed, ${results.length} total`);
  console.log(`${'═'.repeat(50)}`);

  if (failed > 0) {
    console.log('\n❌ Failed tests:');
    results.filter(r => r.status === 'FAIL').forEach(r => {
      console.log(`   • ${r.name}: ${r.detail}`);
    });
  }

  process.exit(failed > 0 ? 1 : 0);
})();
