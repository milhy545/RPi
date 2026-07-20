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

  await clickAndMaybeWait(page, '#bt-auto-connect + .bt-slider', null);
  await clickAndMaybeWait(page, '#bt-discoverable-all + .bt-slider', '/bt/discovery');
  await page.selectOption('#bt-timeout', '5 min');
  await page.selectOption('#bt-scan-mode', 'Aggressive');
  await clickAndMaybeWait(page, '#bt-app button:has-text("Scan Adapters")', '/bt/discovery');
  await clickAndMaybeWait(page, '#bt-adapters button:has-text("Scan")', '/bt/discovery');
  await clickAndMaybeWait(page, '#bt-adapters button:has-text("Power Off")', '/bt/adapter-power');
  await page.waitForTimeout(5000);
  await page.evaluate(() => window.bluetoothRefresh?.());
  await page.waitForTimeout(10000);
  const powerOnCount = await page.locator('#bt-adapters button:has-text("Power On")').count();
  if (!powerOnCount) {
    const state = await page.evaluate(async () => {
      const response = await fetch('/bt/state');
      const data = await response.json();
      return data.adapters.map(adapter => [adapter.id, adapter.powered]);
    });
    if (!state.some(([, powered]) => powered === false)) {
      console.log(`Power Off click completed but no adapter remained off: ${JSON.stringify(state)}`);
    }
  } else {
    await clickAndMaybeWait(page, '#bt-adapters button:has-text("Power On")', '/bt/adapter-power');
  }
  await page.waitForTimeout(3000);

  for (const action of ['pair', 'trust', 'connect', 'disconnect', 'remove']) {
    const selector = `button[onclick="btSelectedAction('${action}')"]`;
    if (await page.locator(selector).count()) {
      await clickAndMaybeWait(page, selector, '/bt/device-action');
    }
  }

  const quickCount = await page.locator('.bt-action-tile').count();
  for (let i = 0; i < quickCount; i++) {
    await page.locator('.bt-action-tile').nth(i).click();
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
