import { chromium } from '@playwright/test';

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext();
const page = await context.newPage();

async function getH3() {
  const h3 = page.locator('h3').first();
  return await h3.textContent().catch(() => '(no h3)');
}

console.log('Logging in...');
await page.goto('http://localhost:3000');
await page.waitForTimeout(500);

const inputs = await page.locator('input').all();
await inputs[0].fill('admin');
await inputs[1].fill('admin');
await page.click('button:has-text("Sign in")');
await page.waitForTimeout(2000);

console.log('Initial content:', await getH3());
console.log('URL:', page.url());

const navItems = [
  'Dashboard',
  'Cost explorer',
  'Projects',
  'Connections',
  'Alerts',
  'Run log',
  'Budgets',
  'Settings'
];

for (const label of navItems) {
  await page.click(`button:has-text("${label}")`);
  await page.waitForTimeout(1000);
  const content = await getH3();
  const activeBtn = await page.locator('button.fn-nav-item.is-active').textContent();
  console.log(`→ ${label}: h3="${content}" active="${activeBtn?.trim()}"`);
}

await browser.close();