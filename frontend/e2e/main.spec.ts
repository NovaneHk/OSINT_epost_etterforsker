import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@localhost';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'yNP!X2&g!rshw*)Bk^3V*V!q';

test.describe('OSINT Email Investigator E2E Tests', () => {
    test('login flow', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[type="email"]', ADMIN_EMAIL);
        await page.fill('input[type="password"]', ADMIN_PASSWORD);
        await page.click('button[type="submit"]');
        
        // Verify redirect to dashboard (locale prefix may be added)
        await expect(page).toHaveURL(/\/dashboard/);
    });

    test('leads page loads after login', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[type="email"]', ADMIN_EMAIL);
        await page.fill('input[type="password"]', ADMIN_PASSWORD);
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/\/dashboard/);
        
        await page.goto('/leads');
        await expect(page).toHaveURL(/\/leads/);
        await expect(page.locator('h1')).toBeVisible();
    });

    test('logout flow', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[type="email"]', ADMIN_EMAIL);
        await page.fill('input[type="password"]', ADMIN_PASSWORD);
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/\/dashboard/);

        // Click user menu and logout
        await page.click('[data-testid="user-menu"]');
        await page.click('text=Logout');

        // Should redirect to login
        await expect(page).toHaveURL(/\/login/);
    });

    // Placeholder tests that previously tested non-existent features
    test('contact management', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[type="email"]', ADMIN_EMAIL);
        await page.fill('input[type="password"]', ADMIN_PASSWORD);
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/\/dashboard/);
        
        await page.goto('/leads');
        await page.waitForSelector('[data-testid="leads-table"], [data-testid="empty-state"]', { timeout: 15000 });
        await expect(page.locator('table')).toBeVisible();
    });

    test('export functionality', async ({ page }) => {
        await page.goto('/login');
        await page.fill('input[type="email"]', ADMIN_EMAIL);
        await page.fill('input[type="password"]', ADMIN_PASSWORD);
        await page.click('button[type="submit"]');
        await expect(page).toHaveURL(/\/dashboard/);

        await page.goto('/leads');
        await page.waitForSelector('[data-testid="leads-table"], [data-testid="empty-state"]', { timeout: 15000 });
        // Export button exists on leads page
        await expect(page.locator('[data-testid="export-leads"]')).toBeVisible();
        
        // Start export (triggers CSV download)
        const downloadPromise = page.waitForEvent('download');
        await page.click('[data-testid="export-leads"]');
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toContain('.csv');
    });
});