import { test } from "@playwright/test";

test("capture landing page screenshot", async ({ page }) => {
  console.log("Navigating to landing page...");
  await page.goto("/");
  
  console.log("Waiting for 3D molecular canvas and Flickering Grid animations to stabilize...");
  await page.waitForTimeout(5000); // 5 seconds of stabilization for a high-fidelity screenshot
  
  const screenshotPath = 'C:\\Users\\KangyongMa\\.gemini\\antigravity-cli\\brain\\8b1e90f6-8663-43de-8e85-2ec4c1d48e5c\\landing_screenshot.png';
  console.log(`Saving optimized landing page screenshot to: ${screenshotPath}`);
  
  await page.screenshot({ path: screenshotPath });
  console.log("Screenshot successfully saved!");
});
