import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@localhost';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'yNP!X2&g!rshw*)Bk^3V*V!q';

test.describe('Lead Management', () => {
  test.beforeEach(async ({ page }) => {
    // Login and wait for dashboard redirect
    await page.goto('/login');
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);

    // Navigate to leads page and wait for it to load
    await page.goto('/leads');
    await expect(page).toHaveURL(/\/leads/);
    // Wait for the page to finish loading (either table or empty state)
    await page.waitForSelector('[data-testid="leads-table"], [data-testid="empty-state"]', { timeout: 15000 });
  });

  test('should display leads page with table', async ({ page }) => {
    await expect(page).toHaveURL(/\/leads/);
    await expect(page.locator('h1')).toContainText('Email Leads');

    // Should see leads table
    await expect(page.locator('[data-testid="leads-table"]')).toBeVisible();

    // Should see filter bar
    await expect(page.locator('[data-testid="filter-bar"]')).toBeVisible();

    // Should see add lead button
    await expect(page.locator('button:has-text("Add Lead")')).toBeVisible();
  });

  test('should filter leads by email domain', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Apply domain filter
    await page.fill('[data-testid="domain-filter"]', 'example.com');
    await page.click('[data-testid="apply-filter"]');

    // Should only show leads with example.com domain
    const leads = page.locator('[data-testid="leads-table"] tbody tr');
    await expect(leads.first().locator('td:nth-child(2)')).toContainText('@example.com');
  });

  test('should sort leads by confidence score', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Click confidence score column header twice to sort descending (first click = ascending, second = descending)
    await page.click('[data-testid="confidence-header"]');
    await page.click('[data-testid="confidence-header"]');

    // Check that leads are sorted by confidence score descending
    const firstScore = await page.locator('[data-testid="leads-table"] tbody tr:first-child [data-testid="confidence-score"]').textContent();
    const secondScore = await page.locator('[data-testid="leads-table"] tbody tr:nth-child(2) [data-testid="confidence-score"]').textContent();

    expect(parseInt(firstScore || '0')).toBeGreaterThanOrEqual(parseInt(secondScore || '0'));
  });

  test('should open lead details modal', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Click on first lead
    await page.click('[data-testid="leads-table"] tbody tr:first-child [data-testid="view-lead"]');

    // Should open modal
    await expect(page.locator('[data-testid="lead-modal"]')).toBeVisible();
    await expect(page.locator('[data-testid="lead-modal"] h2')).toContainText('Lead Details');

    // Should show lead information
    await expect(page.locator('[data-testid="lead-email"]')).toBeVisible();
    await expect(page.locator('[data-testid="lead-company"]')).toBeVisible();
    await expect(page.locator('[data-testid="lead-confidence"]')).toBeVisible();
  });

  test('should close lead details modal', async ({ page }) => {
    // Open modal first
    await page.click('[data-testid="leads-table"] tbody tr:first-child [data-testid="view-lead"]');
    await expect(page.locator('[data-testid="lead-modal"]')).toBeVisible();

    // Close modal using X button
    await page.click('[data-testid="close-modal"]');
    await expect(page.locator('[data-testid="lead-modal"]')).not.toBeVisible();
  });

  test('should export leads to CSV', async ({ page }) => {
    // Set up download promise before triggering the download
    const downloadPromise = page.waitForEvent('download');

    // Click export button
    await page.click('[data-testid="export-leads"]');

    // Wait for download to start
    const download = await downloadPromise;

    // Verify download
    expect(download.suggestedFilename()).toMatch(/leads.*\.csv$/);
  });

  test('should add new lead manually', async ({ page }) => {
    // Click add lead button
    await page.click('button:has-text("Add Lead")');

    // Should open add lead dialog
    await expect(page.locator('[data-testid="add-lead-dialog"]')).toBeVisible();

    // Fill form
    await page.fill('[data-testid="lead-email-input"]', 'newlead@test.com');
    await page.fill('[data-testid="lead-name-input"]', 'New Test Lead');
    await page.fill('[data-testid="lead-company-input"]', 'Test Company');

    // Submit form
    await page.click('[data-testid="save-lead"]');

    // Should show success message
    await expect(page.locator('text=Lead added successfully')).toBeVisible();

    // Should close dialog
    await expect(page.locator('[data-testid="add-lead-dialog"]')).not.toBeVisible();

    // Should see new lead in table
    await expect(page.locator('text=newlead@test.com')).toBeVisible();
  });

  test('should validate add lead form', async ({ page }) => {
    // Click add lead button
    await page.click('button:has-text("Add Lead")');

    // Try to submit empty form
    await page.click('[data-testid="save-lead"]');

    // Should show validation errors
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Name is required')).toBeVisible();
    await expect(page.locator('text=Company is required')).toBeVisible();
  });

  test('should delete lead', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Get initial count
    const initialCount = await page.locator('[data-testid="leads-table"] tbody tr').count();

    // Click delete button on first lead
    await page.click('[data-testid="leads-table"] tbody tr:first-child [data-testid="delete-lead"]');

    // Confirm deletion in dialog
    await expect(page.locator('[data-testid="confirm-dialog"]')).toBeVisible();
    await page.click('[data-testid="confirm-delete"]');

    // Should show success message
    await expect(page.locator('text=Lead deleted successfully')).toBeVisible();

    // Should have one less lead
    await expect(page.locator('[data-testid="leads-table"] tbody tr')).toHaveCount(initialCount - 1);
  });

  test('should cancel lead deletion', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Get initial count
    const initialCount = await page.locator('[data-testid="leads-table"] tbody tr').count();

    // Click delete button on first lead
    await page.click('[data-testid="leads-table"] tbody tr:first-child [data-testid="delete-lead"]');

    // Cancel deletion in dialog
    await expect(page.locator('[data-testid="confirm-dialog"]')).toBeVisible();
    await page.click('[data-testid="cancel-delete"]');

    // Should close dialog
    await expect(page.locator('[data-testid="confirm-dialog"]')).not.toBeVisible();

    // Should still have same number of leads
    await expect(page.locator('[data-testid="leads-table"] tbody tr')).toHaveCount(initialCount);
  });

  test('should search leads by name', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Search for specific lead
    await page.fill('[data-testid="search-input"]', 'John Doe');
    await page.press('[data-testid="search-input"]', 'Enter');

    // Should filter results
    const visibleRows = page.locator('[data-testid="leads-table"] tbody tr:visible');
    const visibleCount = await visibleRows.count();
    expect(visibleCount).toBeGreaterThan(0);

    // All visible rows should contain search term
    const firstResult = visibleRows.first();
    await expect(firstResult).toContainText('John Doe');
  });

  test('should clear search filter', async ({ page }) => {
    // Apply search first (client-side filter)
    await page.fill('[data-testid="search-input"]', 'John Doe');
    await page.waitForTimeout(300);

    // Clear search
    await page.fill('[data-testid="search-input"]', '');

    // Wait for filter to clear - second row should become visible again
    await expect(page.locator('[data-testid="leads-table"] tbody tr').nth(1)).toBeVisible({ timeout: 5000 });

    // Should show all leads again
    const allLeadsCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(allLeadsCount).toBeGreaterThanOrEqual(1);
  });

  test('should handle pagination', async ({ page }) => {
    // Assuming we have pagination
    const paginationExists = await page.locator('[data-testid="pagination"]').isVisible();

    if (paginationExists) {
      // Click next page
      await page.click('[data-testid="next-page"]');

      // URL should change to include page parameter
      await expect(page).toHaveURL(/.*page=2.*/);

      // Should load new leads
      const pageLeadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
      expect(pageLeadCount).toBeGreaterThan(0);

      // Go back to first page
      await page.click('[data-testid="prev-page"]');
      await expect(page).toHaveURL(/.*page=1.*|^(?!.*page=).*/);
    }
  });

  test('should display empty state when no leads', async ({ page }) => {
    // Apply a filter that returns no results
    await page.fill('[data-testid="search-input"]', 'nonexistentlead12345');
    await page.press('[data-testid="search-input"]', 'Enter');

    // Should show empty state
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
    await expect(page.locator('text=No leads found')).toBeVisible();
  });
});

test.describe('Lead Management - Batch Operations', () => {
  test.beforeEach(async ({ page }) => {
    // Login and navigate to leads
    await page.goto('/login');
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL(/\/dashboard/);
    await page.goto('/leads');
    await expect(page).toHaveURL(/\/leads/);
    await page.waitForSelector('[data-testid="leads-table"], [data-testid="empty-state"]', { timeout: 15000 });
  });

  test('should select multiple leads', async ({ page }) => {
    // Wait for leads to load
    const leadCount = await page.locator('[data-testid="leads-table"] tbody tr').count();
    expect(leadCount).toBeGreaterThan(0);

    // Select first two leads
    await page.check('[data-testid="leads-table"] tbody tr:first-child input[type="checkbox"]');
    await page.check('[data-testid="leads-table"] tbody tr:nth-child(2) input[type="checkbox"]');

    // Should show batch actions
    await expect(page.locator('[data-testid="batch-actions"]')).toBeVisible();
    await expect(page.locator('[data-testid="selected-count"]')).toContainText('2 selected');
  });

  test('should export selected leads', async ({ page }) => {
    // Select leads
    await page.check('[data-testid="leads-table"] tbody tr:first-child input[type="checkbox"]');
    await page.check('[data-testid="leads-table"] tbody tr:nth-child(2) input[type="checkbox"]');

    // Set up download promise
    const downloadPromise = page.waitForEvent('download');

    // Click export selected
    await page.click('[data-testid="export-selected"]');

    // Verify download
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/selected-leads.*\.csv$/);
  });

  test('should delete selected leads', async ({ page }) => {
    // Select leads
    await page.check('[data-testid="leads-table"] tbody tr:first-child input[type="checkbox"]');
    await page.check('[data-testid="leads-table"] tbody tr:nth-child(2) input[type="checkbox"]');

    // Delete selected
    await page.click('[data-testid="delete-selected"]');

    // Confirm deletion
    await expect(page.locator('[data-testid="confirm-dialog"]')).toBeVisible();
    await page.click('[data-testid="confirm-delete"]');

    // Should show success message
    await expect(page.locator('text=2 leads deleted successfully')).toBeVisible();
  });
});