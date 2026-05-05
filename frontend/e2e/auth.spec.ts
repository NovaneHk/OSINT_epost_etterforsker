import { test, expect } from '@playwright/test';

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? 'admin@localhost';
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? 'yNP!X2&g!rshw*)Bk^3V*V!q';

test.describe('Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('should display login page when not authenticated', async ({ page }) => {
    // Check if we're redirected to login or see login form
    await expect(page).toHaveURL(/.*login.*|.*auth.*/);

    // Should see login form elements
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('should show validation errors for invalid login', async ({ page }) => {
    await page.goto('/login');

    // Try to submit without credentials
    await page.click('button[type="submit"]');

    // Should show validation errors
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill invalid credentials
    await page.fill('input[type="email"]', 'invalid@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill valid credentials (these would be test credentials)
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL(/\/dashboard/);

    // Should see dashboard content
    await expect(page.locator('h1')).toContainText('Dashboard');
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should logout successfully', async ({ page }) => {
    // First login
    await page.goto('/login');
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/dashboard/);

    // Click user menu and logout
    await page.click('[data-testid="user-menu"]');
    await page.click('text=Logout');

    // Should redirect to login
    await expect(page).toHaveURL(/.*login.*|.*auth.*/);
  });

  test('should persist authentication across page reloads', async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL(/\/dashboard/);

    // Reload page
    await page.reload();

    // Should still be authenticated
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('[data-testid="user-menu"]')).toBeVisible();
  });

  test('should redirect to intended page after login', async ({ page }) => {
    // Try to access protected page directly
    await page.goto('/leads');

    // Should be redirected to login
    await expect(page).toHaveURL(/.*login.*|.*auth.*/);

    // Login
    await page.fill('input[type="email"]', ADMIN_EMAIL);
    await page.fill('input[type="password"]', ADMIN_PASSWORD);
    await page.click('button[type="submit"]');

    // Should be redirected to originally intended page
    await expect(page).toHaveURL(/\/leads/);
  });
});

test.describe('Authentication - Password Reset', () => {
  test('should show forgot password form', async ({ page }) => {
    await page.goto('/login');

    await page.click('text=Forgot password?');

    await expect(page).toHaveURL(/.*forgot-password.*|.*reset.*/);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText(/send.*reset.*link/i);
  });

  test('should validate email for password reset', async ({ page }) => {
    await page.goto('/forgot-password');

    // Try invalid email
    await page.fill('input[type="email"]', 'invalid-email');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Please enter a valid email')).toBeVisible();
  });

  test('should send password reset email', async ({ page }) => {
    await page.goto('/forgot-password');

    await page.fill('input[type="email"]', 'user@example.com');
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Password reset link sent')).toBeVisible();
  });
});

test.describe('Authentication - Registration', () => {
  test('should show registration form', async ({ page }) => {
    await page.goto('/login');

    await page.click('text=Create account');

    await expect(page).toHaveURL(/.*register.*|.*signup.*/);
    await expect(page.locator('input[name="name"]')).toBeVisible();
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('input[name="confirmPassword"]')).toBeVisible();
  });

  test('should validate registration form', async ({ page }) => {
    await page.goto('/register');

    // Submit empty form
    await page.click('button[type="submit"]');

    await expect(page.locator('text=Name is required')).toBeVisible();
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should validate password confirmation', async ({ page }) => {
    await page.goto('/register');

    await page.fill('input[name="name"]', 'Test User');
    await page.fill('input[type="email"]', 'test@example.com');
    await page.fill('input[type="password"]', 'password123');
    await page.fill('input[name="confirmPassword"]', 'different123');

    await page.click('button[type="submit"]');

    await expect(page.locator('text=Passwords do not match')).toBeVisible();
  });

  test('should register new user successfully', async ({ page }) => {
    await page.goto('/register');

    const uniqueEmail = `testuser${Date.now()}@example.com`;
    await page.fill('input[name="name"]', 'Test User');
    await page.fill('input[type="email"]', uniqueEmail);
    await page.fill('input[name="password"]', 'Password123!');
    await page.fill('input[name="confirmPassword"]', 'Password123!');

    await page.click('button[type="submit"]');

    // Should show success message or redirect to verification
    await expect(page.locator('text=Account created successfully')).toBeVisible();
  });
});