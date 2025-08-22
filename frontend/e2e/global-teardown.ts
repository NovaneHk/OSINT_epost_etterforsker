import { FullConfig } from '@playwright/test';

async function globalTeardown(config: FullConfig) {
  console.log('Running global teardown...');

  // Clean up any global resources
  // For example, clean up test data, close databases, etc.

  // If you created any temporary files during tests, clean them up
  // If you have test databases, clean them up

  console.log('Global teardown completed');
}

export default globalTeardown;