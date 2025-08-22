import { chromium, FullConfig } from '@playwright/test';

async function globalSetup(config: FullConfig) {
  // Create a browser instance for global setup
  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    // Wait for the development server to be ready
    console.log('Waiting for development server to be ready...');
    await page.goto('http://localhost:3000', { waitUntil: 'networkidle' });
    console.log('Development server is ready!');

    // You can add authentication setup here if needed
    // For example, login as admin user for authenticated tests

    // Store authentication state if needed
    // await page.context().storageState({ path: 'e2e/auth-state.json' });

  } catch (error) {
    console.error('Global setup failed:', error);
    throw error;
  } finally {
    await browser.close();
  }
}

export default globalSetup;