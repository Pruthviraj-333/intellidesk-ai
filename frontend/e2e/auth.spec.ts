import { test, expect } from '@playwright/test';

/**
 * E2E — Authentication Flow Tests
 *
 * Requirements:
 *  - Vite dev server on localhost:5173 (auto-started via playwright.config.ts webServer)
 *  - Backend API on localhost:8000 (Docker containers must be running: `docker-compose up -d`)
 *
 * Seed credentials: employee@intellidesk.ai / Employee@123!
 */

// Helper: navigate to /login with a clean slate (no tokens)
async function goToLoginFresh(page: import('@playwright/test').Page) {
  // Clear localStorage before the page even loads to avoid race conditions and auto-logins
  await page.context().addInitScript(() => {
    window.localStorage.clear();
  });
  
  await page.goto('/login');
  
  // Wait for any Loading spinner to be completely gone
  await page.locator('text=Loading...').waitFor({ state: 'detached', timeout: 5000 }).catch(() => {});
  
  // Ensure the login form email input is visible and ready
  await page.locator('#email').waitFor({ state: 'visible', timeout: 5000 });
}

// Helper: fill and submit the login form
async function submitLoginForm(
  page: import('@playwright/test').Page,
  email: string,
  password: string,
) {
  // Use standard locator.fill() which is fast and triggers react input events
  const emailInput = page.locator('#email');
  await emailInput.fill(email);
  await expect(emailInput).toHaveValue(email);

  const passwordInput = page.locator('#password');
  await passwordInput.fill(password);
  await expect(passwordInput).toHaveValue(password);

  await page.locator('[data-testid="login-submit"]').click();
}

test.describe('Authentication Flow E2E', () => {
  test.beforeEach(async ({ page }) => {
    page.on('console', msg => console.log('BROWSER LOG:', msg.text()));
    page.on('pageerror', err => console.log('BROWSER ERROR:', err.message));
  });

  test('redirects unauthenticated users from / to /login', async ({ page }) => {
    await page.context().addInitScript(() => {
      window.localStorage.clear();
    });
    await page.goto('/');

    // DashboardLayout has an auth guard: redirects to /login when not authenticated
    await page.waitForURL(/\/login/, { timeout: 10000 });
    await expect(page.getByRole('heading', { name: 'Welcome Back' })).toBeVisible();
  });

  test('login page renders all required form elements', async ({ page }) => {
    await goToLoginFresh(page);
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.locator('[data-testid="login-submit"]')).toBeVisible();
    await expect(page.getByText("Don't have an account?")).toBeVisible();
  });

  test('shows error banner with incorrect credentials', async ({ page }) => {
    await goToLoginFresh(page);
    await submitLoginForm(page, 'employee@intellidesk.ai', 'WrongPassword!99');

    // Wait for the error banner to appear (API responds and component re-renders)
    const errorBanner = page.locator('[data-testid="login-error"]');
    await expect(errorBanner).toBeVisible({ timeout: 10000 });
    await expect(errorBanner).toContainText(/invalid email or password/i);
  });

  test('logs in successfully and redirects to dashboard', async ({ page }) => {
    await goToLoginFresh(page);
    await submitLoginForm(page, 'employee@intellidesk.ai', 'Employee@123!');

    // Should redirect away from /login after successful auth
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 12000 });

    // Dashboard heading should be visible
    await expect(page.locator('body')).toContainText('Dashboard');
  });
});
