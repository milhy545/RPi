import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const TARGET = process.env.TARGET_URL || 'http://192.168.0.205:8090';
const ARTIFACTS = './artifacts';
mkdirSync(ARTIFACTS, { recursive: true });

async function clickAndMaybeWait(page, selector, pattern, timeout = 45000) {
  const wait = pattern
    ? page.waitForResponse(r => r.url().includes(pattern), { timeout }).catch(e => ({ timeout: String(e) }))
    : Promise.resolve(null);
  await page.click(selector, { timeout: 20000 });
  const response = await wait;
  if (pattern) {
    if (!response || response.timeout) throw new Error(`${selector} did not receive ${pattern}: ${response?.timeout || 'no response'}`);
    const payload = await response.json().catch(error => ({ ok: false, error: `Invalid JSON: ${error}` }));
    if (!response.ok() || payload.ok !== true) throw new Error(`${selector} failed: ${JSON.stringify(payload)}`);
  }
  await page.waitForTimeout(1000);
  return response;
}

async function screenshotViewport(page, name, width, height) {
  await page.setViewportSize({ width, height });
  await page.evaluate(() => {
    window.sw?.('bluetooth');
    window.btInitInteractions?.();
    window.btCenterCanvas?.(true);
    window.btDrawTopologyLines?.();
  });
  await page.waitForTimeout(1200);
  const visible = await page.evaluate(() => {
    return ['#bt-app', '.bt-topnav', '.bt-area-topo', '#bt-status', '#bt-device-details'].every(selector => {
      const el = document.querySelector(selector);
      if (!el) return false;
      const rect = el.getBoundingClientRect();
      return rect.width > 0 && rect.height > 0 && rect.right > 0 && rect.left < window.innerWidth;
    });
  });
  if (!visible) throw new Error(`${name} viewport has hidden or offscreen required BT UI`);
  await page.screenshot({ path: `${ARTIFACTS}/bt-real-${name}.png`, fullPage: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  const errors = [];
  page.on('console', msg => {
    if (msg.type() === 'error' && !msg.text().includes('Failed to load resource')) {
      errors.push(msg.text());
    }
  });
  page.on('pageerror', err => errors.push(String(err)));
  page.on('dialog', dialog => dialog.accept());

  await page.goto(TARGET, { waitUntil: 'domcontentloaded', timeout: 30000 });
  await page.click('#tab-bluetooth');
  await page.waitForSelector('#bt-app.mode-advanced', { timeout: 30000 });
  await page.waitForSelector('#bt-topology', { state: 'attached', timeout: 30000 });
  await page.waitForFunction(
    () => document.querySelectorAll('.bt-device-node').length > 0,
    { timeout: 90000 },
  );

  await screenshotViewport(page, 'desktop', 1500, 950);
  await screenshotViewport(page, 'tablet', 900, 1100);
  await screenshotViewport(page, 'mobile', 390, 844);
  await page.setViewportSize({ width: 1500, height: 950 });

  await page.click('#bt-btn-basic');
  await page.waitForSelector('#bt-app.mode-basic');
  await page.click('#bt-btn-advanced');
  await page.waitForSelector('#bt-app.mode-advanced');
  await page.click('button[aria-label="Bluetooth theme"]');
  await page.waitForSelector('#bt-app.bt-theme-light');
  await page.click('button[aria-label="Bluetooth language"]');

  for (const selector of ['#bt-filter-connected', '#bt-filter-paired', '#bt-filter-available']) {
    await page.click(selector);
    await page.click(selector);
  }
  for (const selector of [
    'button[aria-label="Zoom in"]',
    'button[aria-label="Zoom out"]',
    'button[aria-label="Reset topology"]',
  ]) {
    await page.click(selector);
  }

  await page.waitForFunction(
    () => document.querySelectorAll('.bt-device-node').length > 0,
    { timeout: 90000 },
  );
  const nodeCount = await page.locator('.bt-device-node').count();
  if (nodeCount < 1) throw new Error('No real Bluetooth device nodes rendered');
  await page.locator('.bt-device-node').first().click();

  await clickAndMaybeWait(page, '#bt-auto-connect + .bt-slider', '/bt/settings');
  await clickAndMaybeWait(page, '#bt-discoverable-all + .bt-slider', '/bt/discoverable');
  await Promise.all([
    page.waitForResponse(response => response.url().includes('/bt/settings')),
    page.selectOption('#bt-timeout', '300'),
  ]);
  await Promise.all([
    page.waitForResponse(response => response.url().includes('/bt/settings')),
    page.selectOption('#bt-scan-mode', 'aggressive'),
  ]);
  await clickAndMaybeWait(page, '#bt-app button:has-text("Scan Adapters")', '/bt/discovery');
  await clickAndMaybeWait(page, '#bt-adapters button:has-text("Scan")', '/bt/discovery');
  const autoConnectOff = await page.evaluate(async () => (
    await (await fetch('/bt/settings?auto_connect=0')).json()
  ));
  if (autoConnectOff.ok !== true) throw new Error(`Failed to disable Auto Connect for action tests: ${JSON.stringify(autoConnectOff)}`);

  for (const action of ['pair', 'trust', 'disconnect', 'connect', 'remove']) {
    const selected = await page.evaluate(async actionName => {
      const predicate = {
        pair: device => device.paired,
        trust: device => !device.trusted || device.paired,
        connect: device => device.paired && !device.connected,
        disconnect: device => device.connected,
        remove: device => device.present !== false && !device.paired,
      }[actionName];
      let device;
      for (let attempt = 0; attempt < 30; attempt++) {
        const freshState = await (await fetch('/bt/state')).json();
        window.renderBluetoothState(freshState);
        device = (BT_UI?.state?.devices || []).find(predicate);
        if (device) break;
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      if (!device) {
        return {
          ok: false,
          devices: (BT_UI?.state?.devices || []).map(item => ({
            name: item.name,
            paired: item.paired,
            trusted: item.trusted,
            connected: item.connected,
            present: item.present,
          })),
        };
      }
      BT_UI.selected = btStableKey(device);
      if (actionName === 'pair') device.paired = false;
      if (actionName === 'trust') device.trusted = false;
      window.btRenderCurrent();
      return { ok: true };
    }, action);
    if (!selected.ok) throw new Error(`No real device matched the ${action} test state: ${JSON.stringify(selected.devices)}`);
    const selector = `button[onclick="btSelectedAction('${action}')"]`;
    if (await page.locator(selector).isDisabled()) throw new Error(`${action} action is unexpectedly disabled`);
    await clickAndMaybeWait(page, selector, '/bt/device-action');
    await page.evaluate(() => window.bluetoothRefresh());
    await page.waitForTimeout(500);
  }

  await clickAndMaybeWait(page, '#bt-adapters button:has-text("Power Off")', '/bt/adapter-power');
  await page.waitForTimeout(3000);

  const restore = await page.evaluate(async () => {
    const state = await (await fetch('/bt/state')).json();
    const results = [];
    for (const adapter of state.adapters.filter(candidate => candidate.present && !candidate.powered)) {
      results.push(await (await fetch(`/bt/adapter-power?adapter_id=${encodeURIComponent(adapter.id)}&powered=1`)).json());
    }
    return results;
  });
  if (restore.some(result => result.ok !== true)) throw new Error(`Adapter power restore failed: ${JSON.stringify(restore)}`);

  const quickCount = await page.locator('.bt-action-tile').count();
  for (let i = 0; i < quickCount; i++) {
    const tile = page.locator('.bt-action-tile').nth(i);
    if (!(await tile.isDisabled())) await tile.click();
    await page.waitForTimeout(1000);
  }

  await page.screenshot({ path: `${ARTIFACTS}/bt-real-clicked-all.png`, fullPage: true });
  if (errors.length) throw new Error(`Console errors: ${errors.join('; ')}`);

  await browser.close();
  console.log(`REAL_RPI_WEBUI_BT_E2E passed nodes=${nodeCount} quick=${quickCount}`);
})().catch(async err => {
  console.error(err);
  process.exit(1);
});
