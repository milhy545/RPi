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
    { id: 'adapter-uart', index: 0, bluez_path: '/org/bluez/hci0', address: 'AA:AA:AA:AA:AA:01', name: 'hci0 (UART)', bus_type: 'uart', present: true, powered: true, discovering: false },
    { id: 'adapter-usb', index: 1, bluez_path: '/org/bluez/hci1', address: 'BB:BB:BB:BB:BB:02', name: 'hci1 (USB)', bus_type: 'usb', present: true, powered: true, discovering: false },
  ],
  devices: [
    { key: 'adapter-usb/04:50:48:91:22:33', adapter_id: 'adapter-usb', address: '04:50:48:91:22:33', name: 'Samsung Soundbar', kind: 'speaker', connected: true, paired: true, present: true },
    { key: 'adapter-uart/04:50:48:91:22:55', adapter_id: 'adapter-uart', address: '04:50:48:91:22:55', name: 'Xbox Controller', kind: 'gamepad', connected: true, paired: true, present: true },
  ],
  diagnostics: {},
  operations: [],
  events: [],
};

const mockCapabilities = {
  ok: true,
  recommended_audio_adapter: 'adapter-usb',
  recommended_io_adapter: 'adapter-uart',
  adapters: [
    { id: 'adapter-uart', name: 'hci0', index: 0, bus_type: 'uart', bus_label: 'Integrated UART', recommended_roles: ['io'] },
    { id: 'adapter-usb', name: 'hci1', index: 1, bus_type: 'usb', bus_label: 'USB Dongle', recommended_roles: ['audio'] },
  ],
  warning: null,
};

const recordedCalls = [];

(async () => {
  console.log('🚀 Starting Bluetooth Setup Wizard E2E test...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1400, height: 900 } });
  const consoleErrors = [];
  page.on('console', msg => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', err => consoleErrors.push(String(err)));
  page.on('dialog', dialog => dialog.accept());

  // Route API mocks
  await page.route('**/bt/state', route => {
    recordedCalls.push('/bt/state');
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockState) });
  });

  await page.route('**/bt/capabilities', route => {
    recordedCalls.push('/bt/capabilities');
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mockCapabilities) });
  });

  await page.route('**/bt/reset', route => {
    recordedCalls.push('/bt/reset');
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, unpaired_count: 2, unpaired_devices: ['adapter-usb/04:50:48:91:22:33', 'adapter-uart/04:50:48:91:22:55'] }) });
  });

  await page.route('**/bt/discovery*', route => {
    recordedCalls.push(route.request().url());
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, state: 'succeeded' }) });
  });

  await page.route('**/bt/phone-role*', route => {
    recordedCalls.push(route.request().url());
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ ok: true, role: 'sink' }) });
  });

  // Catch-all for remaining APIs
  await page.route('**/*', route => route.continue());

  console.log(`Navigating to ${TARGET}...`);
  await page.goto(TARGET, { waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(500);

  // Switch to Bluetooth tab if not already active
  await page.evaluate(() => {
    if (window.sw) window.sw('bluetooth');
  });
  await page.waitForSelector('#p-bluetooth.active', { timeout: 5000 });

  // 1. Verify default view mode is Basic
  const isBasicDefault = await page.evaluate(() => {
    const root = document.querySelector('#bt-app');
    const basicBtn = document.querySelector('#bt-btn-basic');
    return root && root.classList.contains('mode-basic') && basicBtn && basicBtn.classList.contains('active');
  });
  console.log('✅ Basic view default mode check:', isBasicDefault ? 'PASS' : 'FAIL');
  if (!isBasicDefault) throw new Error('Default view mode is not Basic');

  // 2. Open Wizard Modal
  console.log('Opening Wizard modal...');
  await page.click('button:has-text("Wizard")');
  await page.waitForSelector('#bt-wizard-modal.modal.show', { timeout: 5000 });
  await page.screenshot({ path: `${ARTIFACTS}/bt-wizard-step1.png` });

  const step1Text = await page.textContent('#bt-wizard-body');
  if (!step1Text.includes('Krok 1')) throw new Error('Step 1 content not found');
  console.log('✅ Step 1 (Reset Warning) verified.');

  // 3. Click Next to trigger Reset and move to Step 2
  console.log('Executing Reset & moving to Step 2...');
  const resetPromise = page.waitForResponse(resp => resp.url().includes('/bt/reset'));
  await page.click('#bt-wiz-btn-next');
  await resetPromise;
  await page.waitForTimeout(500);
  await page.screenshot({ path: `${ARTIFACTS}/bt-wizard-step2.png` });

  const step2Text = await page.textContent('#bt-wizard-body');
  console.log('Step 2 Body Text:', JSON.stringify(step2Text));
  if (!step2Text.includes('Krok 2')) throw new Error('Step 2 content not found');
  console.log('✅ Step 2 (Adapter Selection) verified.');

  // 4. Move to Step 3 (IO Pairing)
  console.log('Moving to Step 3 (IO Pairing)...');
  const discoveryIoPromise = page.waitForResponse(resp => resp.url().includes('/bt/discovery'));
  await page.click('#bt-wiz-btn-next');
  await discoveryIoPromise;
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${ARTIFACTS}/bt-wizard-step3.png` });

  const step3Text = await page.textContent('#bt-wizard-body');
  if (!step3Text.includes('Krok 3')) throw new Error('Step 3 content not found');
  console.log('✅ Step 3 (IO Pairing) verified.');

  // 5. Move to Step 4 (Audio Pairing) and test Phone Role
  console.log('Moving to Step 4 (Audio Pairing)...');
  const discoveryAudioPromise = page.waitForResponse(resp => resp.url().includes('/bt/discovery'));
  await page.click('#bt-wiz-btn-next');
  await discoveryAudioPromise;
  await page.waitForTimeout(300);

  const phoneRolePromise = page.waitForResponse(resp => resp.url().includes('/bt/phone-role'));
  await page.selectOption('#bt-wiz-phone-role', 'sink');
  await phoneRolePromise;
  await page.waitForTimeout(300);
  await page.screenshot({ path: `${ARTIFACTS}/bt-wizard-step4.png` });

  const step4Text = await page.textContent('#bt-wizard-body');
  if (!step4Text.includes('Krok 4')) throw new Error('Step 4 content not found');
  console.log('✅ Step 4 (Audio Pairing & Phone Role) verified.');

  // 6. Move to Step 5 (Summary)
  console.log('Moving to Step 5 (Summary)...');
  await page.click('#bt-wiz-btn-next');
  await page.waitForTimeout(400);
  await page.screenshot({ path: `${ARTIFACTS}/bt-wizard-step5.png` });

  const step5Text = await page.textContent('#bt-wizard-body');
  if (!step5Text.includes('Krok 5')) throw new Error('Step 5 content not found');
  console.log('✅ Step 5 (Summary) verified.');

  // 7. Finish Wizard
  console.log('Finishing Wizard...');
  await page.click('#bt-wiz-btn-next');
  await page.waitForTimeout(400);

  const modalVisible = await page.isVisible('#bt-wizard-modal.show');
  console.log('✅ Wizard modal closed:', !modalVisible ? 'PASS' : 'FAIL');
  if (modalVisible) throw new Error('Wizard modal did not close');

  // Check console errors
  if (consoleErrors.length > 0) {
    console.error('❌ Console errors detected:', consoleErrors);
    throw new Error(`Console errors found: ${consoleErrors.join(', ')}`);
  }

  await browser.close();
  console.log('🎉 Bluetooth Setup Wizard E2E Test PASSED SUCCESSFULLY!');
})().catch(err => {
  console.error('❌ E2E TEST FAILED:', err);
  process.exit(1);
});
