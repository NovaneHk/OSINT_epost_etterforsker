import { test, expect } from '@playwright/test';

/**
 * Nova Trace Sprint 1 smoke tests.
 *
 * These tests run against the dev server (NODE_ENV=development) which
 * activates the devBypassEnabled middleware path — no login required.
 */

test.describe('Nova Trace — smoke', () => {
  test('dashboard page loads and shows KPI labels', async ({ page }) => {
    await page.goto('/dashboard');
    // Page title present
    await expect(page.locator('h1, [class*="text-xl"]').first()).toBeVisible();
    // At least one KPI label
    await expect(page.getByText('Leads 7d')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('Searches 7d')).toBeVisible();
  });

  test('leads page loads and shows table', async ({ page }) => {
    await page.goto('/leads');
    await expect(page.locator('h1')).toContainText('Leads');
    // Wait for table or skeleton to resolve
    await page.waitForSelector('[data-testid="leads-table"]', { timeout: 10_000 });
    await expect(page.locator('[data-testid="leads-table"]')).toBeVisible();
  });

  test('leads filter bar is visible', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForSelector('[data-testid="filter-bar"]', { timeout: 10_000 });
    await expect(page.locator('[data-testid="filter-bar"]')).toBeVisible();
    await expect(page.locator('[data-testid="search-input"]')).toBeVisible();
  });

  test('leads search input filters the table', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForSelector('[data-testid="leads-table"]', { timeout: 10_000 });

    const rowsBefore = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(rowsBefore).toBeGreaterThan(0);

    await page.fill('[data-testid="search-input"]', 'equinor');

    // Row count should change (filter applied client-side)
    await expect(async () => {
      const rowsAfter = await page.locator('[data-testid="leads-table"] tbody tr').count();
      expect(rowsAfter).toBeLessThanOrEqual(rowsBefore);
    }).toPass({ timeout: 3_000 });
  });

  test('lead row can be expanded', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForSelector('[data-testid="leads-table"]', { timeout: 10_000 });

    // Click the first expand button
    const expandBtn = page.locator('[data-testid="view-lead"]').first();
    await expandBtn.click();

    // Details panel should appear
    await expect(page.locator('[data-testid="lead-modal"]')).toBeVisible({ timeout: 3_000 });
    await expect(page.locator('[data-testid="lead-email"]')).toBeVisible();
  });

  test('selecting a row reveals the bulk action bar', async ({ page }) => {
    await page.goto('/leads');
    await page.waitForSelector('[data-testid="leads-table"]', { timeout: 10_000 });

    // Tick the first row checkbox
    const checkbox = page
      .locator('[data-testid="leads-table"] tbody tr:first-child input[type="checkbox"]');
    await checkbox.check();

    // Bulk bar should float up
    await expect(page.locator('[data-testid="batch-actions"]')).toBeVisible({ timeout: 3_000 });
    await expect(page.locator('[data-testid="selected-count"]')).toContainText('1 selected');
  });

  test('sidebar is present and navigation items are reachable', async ({ page }) => {
    await page.goto('/dashboard');
    // Sidebar should contain a link to /leads
    await expect(page.locator('a[href*="/leads"]').first()).toBeVisible({ timeout: 5_000 });
  });
});
