import { chromium } from 'playwright';
import { mkdirSync } from 'fs';

const TARGET = process.env.TARGET_URL || 'http://127.0.0.1:8080';
const ARTIFACTS = './artifacts';
mkdirSync(ARTIFACTS, { recursive: true });

const mockState = {
  ok: true,
  schema_version: 2,
  backend: { name: 'fake-e2e', degraded: false },
  adapters: [
    { id: 'hci-a', address: 'AA:AA:AA:AA:AA:01', present: true, powered: true, discovering: false },
    { id: 'hci-b', address: 'BB:BB:BB:BB:BB:02', present: true, powered: true, discovering: false },
  ],
  devices: [
    { key: 'soundbar', adapter_id: 'hci-a', address: '04:50:48:91:22:33', name: 'Samsung Soundbar', kind: 'speaker', connected: true, paired: true, trusted: true, auto_connect: true, present: true, rssi: -48, battery_percentage: null, capabilities: { profiles: [{ id: 'a2dp-sink', label: 'Audio Sink', category: 'audio', direction: 'send', uuid: '0000110b-0000-1000-8000-00805f9b34fb' }], file_transfer: { object_push: false } } },
    { key: 'headphones', adapter_id: 'hci-a', address: '04:50:48:91:22:44', name: 'Sony WH-1000XM4', kind: 'headphones', connected: false, paired: true, trusted: true, auto_connect: false, present: true, rssi: -55, battery_percentage: 88, capabilities: { profiles: [{ id: 'opp', label: 'Object Push', category: 'file_transfer', direction: 'bidirectional', uuid: '00001105-0000-1000-8000-00805f9b34fb' }], file_transfer: { object_push: true } } },
    { key: 'xbox', adapter_id: 'hci-b', address: '04:50:48:91:22:55', name: 'Xbox Controller', kind: 'gamepad', connected: true, paired: true, present: true, rssi: -40, battery_percentage: 72 },
    { key: 'keyboard', adapter_id: 'hci-b', address: '04:50:48:91:22:66', name: 'BT Keyboard', kind: 'keyboard', connected: false, paired: false, present: true, rssi: -58, battery_percentage: null },
  ],
  diagnostics: {
    soundbar: { ready: true, steps: [{ id: 'paired', label: 'Soundbar paired', state: true, reason: 'fake' }] },
    controllers: { ready: true, modules: { uhid: true }, input_devices: ['event8'], steamlink: { available: true }, controllers: ['Xbox Controller'], blockers: [] },
  },
  operations: [],
  events: [{ type: 'scan', message: 'E2E scan complete' }],
  settings: { auto_connect: false, discoverable_timeout: 120, scan_mode: 'balanced' },
};

const requests = [];

function json(route, value) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(value),
  });
}

async function assertViewport(page, name, width, height) {
  await page.setViewportSize({ width, height });
  await page.evaluate(() => {
    window.sw?.('bluetooth');
    window.btInitInteractions?.();
    if (BT_UI?.state) window.renderBluetoothState(BT_UI.state.raw);
  });
  await page.waitForSelector('#p-bluetooth.active');
  await page.waitForSelector('#bt-topology', { state: 'attached' });
  await page.waitForTimeout(300);

  const checks = await page.evaluate(() => {
    const selectors = ['#bt-app', '.bt-topnav', '.bt-area-topo', '#bt-status', '#bt-device-details'];
    return selectors.map(selector => {
      const el = document.querySelector(selector);
      if (!el) return { selector, ok: false, reason: 'missing' };
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return {
        selector,
        ok: r.width > 0 && r.height > 0 && style.display !== 'none' && r.right > 0 && r.left < window.innerWidth,
        rect: { left: r.left, right: r.right, width: r.width, height: r.height },
      };
    });
  });
  for (const check of checks) {
    if (!check.ok) throw new Error(`${name} viewport failed for ${check.selector}: ${JSON.stringify(check)}`);
  }
  const geometry = await page.evaluate(() => {
    const checkboxLefts = [...document.querySelectorAll('.bt-area-filt input[type="checkbox"]')]
      .map(element => Math.round(element.getBoundingClientRect().left));
    const wrapper = document.querySelector('#bt-topo-wrapper')?.getBoundingClientRect();
    const topologyFits = wrapper && [...document.querySelectorAll('.bt-device-node')].every(element => {
      const rect = element.getBoundingClientRect();
      return rect.left >= wrapper.left - 2 && rect.right <= wrapper.right + 2;
    });
    return {
      checkboxLefts,
      topologyFits,
      noHorizontalOverflow: document.documentElement.scrollWidth <= window.innerWidth,
    };
  });
  if (new Set(geometry.checkboxLefts).size !== 1) throw new Error(`${name} filter checkboxes are not aligned: ${geometry.checkboxLefts}`);
  if (!geometry.topologyFits) throw new Error(`${name} topology nodes overflow the canvas`);
  if (!geometry.noHorizontalOverflow) throw new Error(`${name} page has horizontal overflow`);
  await page.screenshot({ path: `${ARTIFACTS}/bt-viewport-${name}.png`, fullPage: true });
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1500, height: 950 } });
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push(String(err)));
  page.on('dialog', dialog => dialog.accept());

  await page.route('**/bt/state', route => {
    requests.push('/bt/state');
    return json(route, mockState);
  });
  await page.route('**/bt/discovery**', route => {
    requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
    return json(route, { ok: true, result: 'discovery ok' });
  });
  await page.route('**/bt/adapter-power**', route => {
    requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
    return json(route, { ok: true, result: 'power ok' });
  });
  await page.route('**/bt/device-action**', route => {
    requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
    return json(route, { ok: true, result: 'device action ok' });
  });
  await page.route('**/bt/device-profile**', route => json(route, { ok: true, result: 'profile action ok' }));
  await page.route('**/bt/pairing**', route => {
    const action = new URL(route.request().url()).searchParams.get('action');
    return json(route, action === 'start'
      ? { ok: true, pairing: { id: 'pair-e2e', state: 'pending' } }
      : { ok: true, pairing: { id: 'pair-e2e', state: 'succeeded' }, challenge: null });
  });
  await page.route('**/bt/device-autoconnect**', route => json(route, { ok: true }));
  await page.route('**/audio/bluetooth-profiles**', route => json(route, { ok: true, cards: [] }));
  await page.route('**/bt/transfers**', route => json(route, { ok: true, receive_agent: true, transfers: [] }));
  await page.route('**/bt/files**', route => json(route, { ok: true, files: [{ name: 'hello.txt', path: '/home/milhy777/Downloads/hello.txt', size: 5 }] }));
  await page.route('**/bt/file-send**', route => json(route, { ok: true, transfer: { id: 'send-1', status: 'active' } }));
  await page.route('**/bt/file-cancel**', route => json(route, { ok: true }));
  await page.route('**/bt/diagnostics**', route => json(route, { ok: true, failure_classes: [], resources: { process_rss: '10 MB', load_average: [0.2, 0.1, 0.1] } }));
  await page.route('**/bt/discoverable**', route => {
    requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
    return json(route, { ok: true, result: 'discoverability ok' });
  });
  await page.route('**/bt/settings**', route => {
    requests.push(new URL(route.request().url()).pathname + new URL(route.request().url()).search);
    return json(route, { ok: true, settings: mockState.settings });
  });
  await page.route('**/youtube/cookies/status', route => json(route, { ok: true }));
  await page.route('**/mpv/status', route => json(route, { on: false }));

  await page.goto(TARGET, { waitUntil: 'domcontentloaded' });
  await page.click('#tab-bluetooth');
  await page.waitForSelector('#bt-app.mode-advanced');
  await page.waitForSelector('#bt-node-0');
  await page.screenshot({ path: `${ARTIFACTS}/bt-01-initial.png`, fullPage: true });

  const requiredText = [
    'RPi Control Center',
    'Správa Topologie Bluetooth',
    'Samsung Soundbar',
    'Xbox Controller',
    'Ovládání Služby',
    'Rychlé akce',
    'Celkový Přehled',
  ];
  for (const text of requiredText) {
    if (!(await page.locator(`text=${text}`).first().isVisible())) throw new Error(`Missing visible text: ${text}`);
  }

  await page.click('#bt-btn-basic');
  if (!(await page.locator('#bt-app.mode-basic').isVisible())) throw new Error('Basic mode did not activate');
  await page.click('#bt-btn-advanced');
  if (!(await page.locator('#bt-app.mode-advanced').isVisible())) throw new Error('Expert mode did not reactivate');
  await page.click('button[aria-label="Bluetooth theme"]');
  if (!(await page.locator('#bt-app.bt-theme-light').isVisible())) throw new Error('Theme toggle failed');
  await page.click('button[aria-label="Bluetooth language"]');
  await page.locator('text=Bluetooth Topology Manager').waitFor({ timeout: 3000 });

  await page.click('#bt-filter-connected');
  await page.click('#bt-filter-paired');
  await page.click('#bt-filter-available');
  await page.click('#bt-filter-connected');
  await page.click('#bt-filter-paired');
  await page.click('#bt-filter-available');

  await page.click('button[aria-label="Zoom in"]');
  await page.click('button[aria-label="Zoom out"]');
  await page.click('button[aria-label="Reset topology"]');
  await page.click('#bt-node-2');
  await page.locator('text=Sony WH-1000XM4').first().waitFor({ timeout: 3000 });

  await page.click('#bt-auto-connect + .bt-slider');
  await page.click('#bt-discoverable-all + .bt-slider');
  await page.selectOption('#bt-timeout', '300');
  await page.selectOption('#bt-scan-mode', 'aggressive');

  await page.click('#bt-app button:has-text("Scan Adapters")');
  await page.click('#bt-app button:has-text("New Device")');
  await page.click('#bt-adapters button:has-text("Scan")');
  await page.click('#bt-adapters button:has-text("Power Off")');
  await page.locator('.bt-device-node', { hasText: 'BT Keyboard' }).click();
  await page.click("button[onclick=\"btSelectedAction('pair')\"]");
  await page.locator('.bt-device-node', { hasText: 'Samsung Soundbar' }).click();
  await page.click("button[onclick=\"btSelectedAction('disconnect')\"]");
  await page.locator('#bt-device-details').getByText('Audio Sink').waitFor();
  await page.click("button[onclick=\"btSelectedAction('block')\"]");
  await page.locator('.bt-device-node', { hasText: 'Sony WH-1000XM4' }).click();
  await page.locator('#bt-device-details').getByText('Object Push').waitFor();
  await page.click('#bt-device-details button:has-text("Send")');
  await page.click("button[onclick=\"btSelectedAction('connect')\"]");
  await page.locator('.bt-device-node', { hasText: 'BT Keyboard' }).click();
  await page.click("button[onclick=\"btSelectedAction('trust')\"]");
  await page.click("button[onclick=\"btSelectedAction('remove')\"]");

  const quickTileCount = await page.locator('.bt-action-tile').count();
  if (quickTileCount !== 8) throw new Error(`Expected 8 quick actions, got ${quickTileCount}`);
  for (let i = 0; i < quickTileCount; i++) {
    const tile = page.locator('.bt-action-tile').nth(i);
    if (!(await tile.isDisabled())) await tile.click();
    await page.waitForTimeout(50);
  }

  await page.screenshot({ path: `${ARTIFACTS}/bt-02-clicked-all.png`, fullPage: true });
  await page.waitForTimeout(4200);

  await assertViewport(page, 'desktop', 1500, 950);
  await assertViewport(page, 'tablet', 900, 1100);
  await assertViewport(page, 'mobile', 390, 844);

  const deviceAction = requests.some(r => r.includes('/bt/device-action') && r.includes('adapter_id=hci-a'));
  const discovery = requests.some(r => r.includes('/bt/discovery'));
  const adapterPower = requests.some(r => r.includes('/bt/adapter-power'));
  const discoverability = requests.some(r => r.includes('/bt/discoverable'));
  const settings = requests.some(r => r.includes('/bt/settings'));
  if (!deviceAction) throw new Error('No adapter-aware device action request was observed');
  if (!discovery) throw new Error('No discovery request was observed');
  if (!adapterPower) throw new Error('No adapter power request was observed');
  if (!discoverability) throw new Error('No discoverability request was observed');
  if (!settings) throw new Error('No Bluetooth settings request was observed');
  if (consoleErrors.length) throw new Error(`Console errors: ${consoleErrors.join('; ')}`);

  await browser.close();
  console.log(`Bluetooth WebUI E2E passed with ${requests.length} mocked BT requests`);
})().catch(async err => {
  console.error(err);
  process.exit(1);
});
