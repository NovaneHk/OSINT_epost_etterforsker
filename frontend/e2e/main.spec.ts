import { test, expect } from '@playwright/test';

test.describe('OSINT Email Investigator E2E Tests', () => {
    test.beforeEach(async ({ page }) => {
        await page.goto('http://localhost:3000');
    });

    test('login flow', async ({ page }) => {
        // Click the login button
        await page.click('text=Login');
        
        // Fill in login form
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'admin');
        await page.click('button[type="submit"]');
        
        // Verify redirect to dashboard
        await expect(page).toHaveURL('/dashboard');
        await expect(page.locator('h1')).toContainText('Welcome back');
    });

    test('contact management', async ({ page }) => {
        // Login first
        await page.goto('http://localhost:3000/login');
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'admin');
        await page.click('button[type="submit"]');
        
        // Navigate to contacts
        await page.click('text=Contacts');
        
        // Check contacts table
        await expect(page.locator('table')).toBeVisible();
        
        // Add new contact
        await page.click('text=Add Contact');
        await page.fill('input[name="email"]', 'test@example.com');
        await page.fill('input[name="name"]', 'Test User');
        await page.click('button[type="submit"]');
        
        // Verify new contact
        await expect(page.locator('table')).toContainText('test@example.com');
    });

    test('export functionality', async ({ page }) => {
        // Login first
        await page.goto('http://localhost:3000/login');
        await page.fill('input[name="username"]', 'admin');
        await page.fill('input[name="password"]', 'admin');
        await page.click('button[type="submit"]');
        
        // Navigate to export
        await page.click('text=Export');
        
        // Set export parameters
        await page.fill('input[name="minScore"]', '0.5');
        
        // Start export
        await page.click('text=Export Contacts');
        
        // Verify download
        const download = await Promise.all([
            page.waitForEvent('download'),
            page.click('text=Download')
        ]);
        
        expect(download[0].suggestedFilename()).toContain('.csv');
    });
});