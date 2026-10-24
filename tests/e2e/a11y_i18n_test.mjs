import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { chromium } from 'playwright';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const html = readFileSync(resolve(root, 'rpi_dashboard/static/index.html'), 'utf8');
const app = readFileSync(resolve(root, 'rpi_dashboard/static/js/app.js'), 'utf8');
const sourceLine = (prefix) => {
  const line = app.split('\n').find((item) => item.startsWith(prefix));
  assert.ok(line, `Missing ${prefix}`);
  return line;
};
const translations = app.slice(app.indexOf('const I18N='), app.indexOf('const HELPERS='));
assert.ok(translations.startsWith('const I18N='));
const bundle = [
  translations,
  "let LANG='cz';",
  sourceLine('function L(k)'),
  sourceLine('function ariaText(k,txt)'),
  sourceLine('function applyLang()'),
  'const $=()=>null; function updateSecurityBanner(){}',
].join('\n');

const browser = await chromium.launch({
  ...(process.env.CHROMIUM_EXECUTABLE_PATH
    ? { executablePath: process.env.CHROMIUM_EXECUTABLE_PATH }
    : {}),
  headless: true,
  args: ['--no-sandbox'],
});
try {
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><body></body></html>');
  await page.evaluate((markup) => {
    const template = new DOMParser().parseFromString(markup, 'text/html');
    for (const selector of [
      '.url-paste',
      '#log-lines',
      'label[for="ta-lat-dlna-offset"]',
      'label[for="login-role"]',
      'label[for="login-password"]',
      '#wifi-ssid',
      'button[onclick="btZoomTopo(0.1)"]',
      'button[onclick="btZoomTopo(-0.1)"]',
      'button[onclick="btResetTopo()"]',
    ]) {
      const element = template.querySelector(selector);
      assert(element, `Missing ${selector}`);
      document.body.append(element.cloneNode(true));
    }
    function assert(value, message) {
      if (!value) throw new Error(message);
    }
  }, html);
  await page.addScriptTag({ content: bundle });

  for (const [language, expected] of [
    ['cz', { paste: 'Vložit schránku', zoomIn: 'Přiblížit', zoomOut: 'Oddálit', resetTopo: 'Obnovit topologii', lines: 'Počet řádků logu', title: 'Počet řádků k načtení', delay: 'Zpoždění zvuku (ms):', password: 'Heslo:' }],
    ['en', { paste: 'Paste clipboard', zoomIn: 'Zoom in', zoomOut: 'Zoom out', resetTopo: 'Reset topology', lines: 'Number of log lines', title: 'Lines to fetch', delay: 'Audio delay (ms):', password: 'Password:' }],
  ]) {
    const actual = await page.evaluate((code) => {
      LANG = code;
      applyLang();
      return {
        paste: document.querySelector('.url-paste').getAttribute('aria-label'),
        pasteTitle: document.querySelector('.url-paste').title,
        pasteIcon: document.querySelector('.url-paste').textContent,
        zoomIn: document.querySelector('button[onclick="btZoomTopo(0.1)"]').getAttribute('aria-label'),
        zoomInIcon: document.querySelector('button[onclick="btZoomTopo(0.1)"]').textContent,
        zoomOut: document.querySelector('button[onclick="btZoomTopo(-0.1)"]').getAttribute('aria-label'),
        zoomOutIcon: document.querySelector('button[onclick="btZoomTopo(-0.1)"]').textContent,
        resetTopo: document.querySelector('button[onclick="btResetTopo()"]').getAttribute('aria-label'),
        resetTopoIcon: document.querySelector('button[onclick="btResetTopo()"]').textContent,
        lines: document.querySelector('#log-lines').getAttribute('aria-label'),
        title: document.querySelector('#log-lines').title,
        delay: document.querySelector('label[for="ta-lat-dlna-offset"]').textContent,
        password: document.querySelector('label[for="login-password"]').textContent,
        role: document.querySelector('label[for="login-role"]').textContent,
        lang: document.documentElement.lang,
      };
    }, language);
    assert.equal(actual.paste, expected.paste);
    assert.equal(actual.pasteTitle, expected.paste);
    assert.equal(actual.pasteIcon, '📋');
    assert.equal(actual.zoomIn, expected.zoomIn);
    assert.equal(actual.zoomInIcon, '＋');
    assert.equal(actual.zoomOut, expected.zoomOut);
    assert.equal(actual.zoomOutIcon, '−');
    assert.equal(actual.resetTopo, expected.resetTopo);
    assert.equal(actual.resetTopoIcon, '⛶');
    assert.equal(actual.lines, expected.lines);
    assert.equal(actual.title, expected.title);
    assert.equal(actual.delay, expected.delay);
    assert.equal(actual.password, expected.password);
    assert.equal(actual.role, 'Role:');
    assert.equal(actual.lang, language === 'cz' ? 'cs' : 'en');
  }
} finally {
  await browser.close();
}
