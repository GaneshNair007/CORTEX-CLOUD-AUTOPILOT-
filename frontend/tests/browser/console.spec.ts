import { test, expect } from '@playwright/test';
import { mockApi, approval, health } from './fixtures';
test.beforeEach(async ({ page }) => { await mockApi(page); });

test('all routed workspaces render without runtime errors', async ({ page }) => {
  const errors: string[] = []; page.on('pageerror', e => errors.push(e.message));
  for (const route of ['console','incidents','topology','events','predictions','simulator','optimizer','memory','cortex','approvals','policies','audit','demo','operations','chaos','reliability','cost','sustainability','evaluation','providers','settings']) {
    await page.goto(`/#/${route}`);
    await expect(page.locator('main h1')).toBeVisible();
    await expect(page.getByText('This view could not render.')).toHaveCount(0);
    await expect(page.getByText('Loading workspace…')).toHaveCount(0);
  }
  expect(errors).toEqual([]);
});
test('incident search and detail use persisted records', async ({ page }) => {
  await page.goto('/#/incidents');
  await page.getByLabel('Search incidents').fill('no-match');
  await expect(page.getByText('No matching incidents')).toBeVisible();
  await page.getByLabel('Search incidents').fill('checkout');
  await page.getByRole('button', { name: 'INC-TEST-101' }).click();
  await expect(page.getByRole('dialog')).toContainText('Connection pool exhausted');
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('offline guard actions are disabled and no fabricated health is shown', async ({ page }) => {
  await page.route('**/api/**', r => r.fulfill({status:502,json:{error:'Test backend offline'}}));
  await page.goto('/#/cortex');
  await expect(page.getByText('Backend unavailable.', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', {name:'Freeze mutations'})).toBeDisabled();
  await expect(page.getByText('99.96%')).toHaveCount(0);
});
test('guard mutation failures do not optimistically change confirmed state', async ({ page }) => {
  await page.route('**/api/cortex/kill-switch', r => r.fulfill({status:500,json:{detail:'Freeze rejected'}}));
  await page.goto('/#/cortex');
  await page.getByRole('button', {name:'Freeze mutations'}).click();
  await expect(page.getByRole('alert')).toContainText('Freeze rejected');
  await expect(page.getByRole('button', {name:'Freeze mutations'})).toBeVisible();
  await expect(page.getByText('Backend confirmed: mutations frozen.')).toHaveCount(0);
});
test('approval requires review and keeps server errors in the dialog', async ({ page }) => {
  let calls = 0;
  await page.route('**/api/cortex/approvals/resolve', r => { calls++; return r.fulfill({json:{status:'expired',message:'Approval expired; re-evaluate.'}}); });
  await page.goto('/#/approvals');
  await page.getByRole('button', {name:'Review approval'}).click();
  expect(calls).toBe(0);
  await expect(page.getByRole('button', {name:'Approve and submit'})).toBeDisabled();
  await page.getByLabel('Operator name').fill('Test operator');
  await page.getByRole('button', {name:'Approve and submit'}).click();
  await expect(page.getByRole('dialog')).toContainText('Approval expired; re-evaluate.');
  expect(calls).toBe(1);
});
test('expired approvals cannot be submitted', async ({ page }) => {
  await page.route('**/api/cortex/approvals', r => r.fulfill({json:{pending_approvals:[{...approval,created_at:1}]}}));
  await page.goto('/#/approvals');
  await expect(page.getByRole('button', {name:'Review approval'})).toBeDisabled();
  await expect(page.getByText('Re-evaluation required')).toBeVisible();
});
test('twin simulation precedes reviewed gateway execution and preserves blocked status', async ({ page }) => {
  const mutations: unknown[] = [];
  page.on('request', r => { if (r.url().endsWith('/api/tools/action')) mutations.push(r.postDataJSON()); });
  await page.goto('/#/simulator');
  await page.getByLabel('Target service', {exact:true}).selectOption('payment-api');
  await page.getByLabel('Target replicas').fill('9');
  await page.getByRole('button', {name:'Simulate change'}).click();
  await page.getByRole('button', {name:'Review execution'}).click();
  expect(mutations).toEqual([]);
  await page.getByRole('button', {name:'Submit through CORTEX'}).click();
  await expect(page.getByText('Blocked by test policy.')).toBeVisible();
  expect(mutations).toEqual([{action_type:'scale_service',params:{service:'payment-api',replicas:9},actor:'console-operator'}]);
});
test('optimizer sends edited inputs and never executes infrastructure', async ({ page }) => {
  let body: unknown; let mutations = 0;
  page.on('request', r => { if (r.url().endsWith('/api/optimizer')) body = r.postDataJSON(); if (r.url().endsWith('/api/tools/action')) mutations++; });
  await page.goto('/#/cost');
  await page.getByLabel('Current replicas').fill('4');
  await page.getByLabel('Forecast demand (RPS)').fill('700');
  await page.getByRole('button', {name:'Compare configurations'}).click();
  await expect(page.getByText('Candidate comparison', {exact:true})).toBeVisible();
  expect(body).toEqual({mode:'COST',current_replicas:4,forecast_rps:700});
  expect(mutations).toBe(0);
});
test('memory retrieves query and displays escaped source content', async ({ page }) => {
  await page.goto('/#/memory');
  await page.getByLabel('Search operational memory').fill('database connection pool');
  await page.getByRole('button', {name:'Search memory',exact:true}).click();
  await expect(page.getByText('Connection pool recovery')).toBeVisible();
  await expect(page.getByText('Review connection limits.')).toBeVisible();
});
test('pipeline renders actual outcome instead of interpreting HTTP success as recovery', async ({ page }) => {
  await page.goto('/#/demo');
  await page.getByLabel('Observed symptom').fill('Payment checkout latency is above the configured target.');
  await page.getByRole('button', {name:'Review control-loop run'}).click();
  await page.getByRole('button', {name:'Run reviewed incident'}).click();
  await expect(page.getByText('BLOCKED', {exact:true}).first()).toBeVisible();
  await expect(page.getByText('Response received', {exact:true})).toHaveCount(9);
});
test('command search works with keyboard and restores focus', async ({ page }) => {
  await page.goto('/#/console');
  await page.keyboard.press('Control+k');
  await page.getByLabel('Search workspaces').fill('digital');
  await page.getByRole('dialog').getByRole('link', {name:'Digital twin'}).click();
  await expect(page).toHaveURL(/#\/simulator/);
  await expect(page.getByRole('dialog')).toHaveCount(0);
});
test('mobile navigation and layouts fit a narrow screen', async ({ page }) => {
  await page.setViewportSize({width:390,height:844});
  await page.goto('/#/console');
  await page.getByRole('button', {name:'Open navigation'}).click();
  await page.getByRole('dialog').getByRole('link', {name:'Predictions',exact:true}).click();
  await expect(page.getByRole('heading', {name:'Predictions',exact:true})).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.screenshot({path:'artifacts/mobile-predictions.png',fullPage:true});
});
test('landing has functional entry points, reduced-motion support, and no mobile overflow', async ({ page }) => {
  await page.emulateMedia({reducedMotion:'reduce'});
  await page.goto('/');
  await expect(page.getByRole('heading', {name:'Cloud complexity. Under control.'})).toBeVisible();
  await page.screenshot({path:'artifacts/landing-desktop.png',fullPage:true});
  await page.setViewportSize({width:390,height:844});
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  await page.getByRole('link', {name:'Launch command center'}).click();
  await expect(page).toHaveURL(/#\/console/);
});
test('provider placeholders cannot claim a connection', async ({ page }) => {
  await page.goto('/#/providers');
  await expect(page.getByText('Not implemented', {exact:true})).toHaveCount(4);
  await expect(page.getByText('Runtime unknown', {exact:true})).toHaveCount(2);
});
test('failed refresh preserves the last snapshot with a stale warning', async ({ page }) => {
  await page.goto('/#/incidents');
  await expect(page.getByText('INC-TEST-101')).toBeVisible();
  await page.route('**/api/incidents', r => r.fulfill({status:503,json:{detail:'Temporarily unavailable'}}));
  await page.getByRole('button', {name:'Refresh data'}).click();
  await expect(page.getByRole('alert')).toContainText('Showing the last snapshot');
  await expect(page.getByText('INC-TEST-101')).toBeVisible();
});
test('connection rejects credential-bearing URLs', async ({ page }) => {
  await page.goto('/#/settings');
  await page.getByLabel('Backend base URL').fill('https://user:password@example.com');
  await page.getByRole('button', {name:'Save connection and reconnect'}).click();
  await expect(page.getByRole('alert')).toContainText('without credentials');
});
test('dashboard screenshot records fixture data without injecting it into production', async ({ page }) => {
  await page.goto('/#/console');
  await expect(page.getByRole('button', {name:'Inspect payment-api'})).toBeVisible();
  await expect(page.getByText('Checkout latency above threshold')).toBeVisible();
  await page.screenshot({path:'artifacts/console-fixture-desktop.png',fullPage:true});
});
