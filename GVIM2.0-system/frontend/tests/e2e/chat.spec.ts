import { expect, test } from "@playwright/test";

import { handleRunStream, mockLangGraphAPI } from "./utils/mock-api";

test.describe("Chat workspace", () => {
  test.beforeEach(async ({ page }) => {
    mockLangGraphAPI(page);
  });

  test("new chat page loads with input box", async ({ page }) => {
    await page.goto("/workspace/chats/new");

    const textarea = page.getByPlaceholder(/how can i assist you/i);
    await expect(textarea).toBeVisible({ timeout: 15_000 });
  });

  test("can type a message in the input box", async ({ page }) => {
    await page.goto("/workspace/chats/new");

    const textarea = page.getByPlaceholder(/how can i assist you/i);
    await expect(textarea).toBeVisible({ timeout: 15_000 });

    await textarea.fill("Hello, GVIM AI!");
    await expect(textarea).toHaveValue("Hello, GVIM AI!");
  });

  test("sending a message triggers API call and shows response", async ({
    page,
  }) => {
    let streamCalled = false;
    await page.route("**/runs/stream", (route) => {
      streamCalled = true;
      return handleRunStream(route);
    });

    await page.goto("/workspace/chats/new");

    const textarea = page.getByPlaceholder(/how can i assist you/i);
    await expect(textarea).toBeVisible({ timeout: 15_000 });

    await textarea.fill("Hello");
    await textarea.press("Enter");

    await expect.poll(() => streamCalled, { timeout: 10_000 }).toBeTruthy();

    // The AI response should appear in the chat
    await expect(page.getByText("Hello from GVIM AI!")).toBeVisible({
      timeout: 10_000,
    });
  });

  test("keeps attachments visible while upload submit is pending", async ({
    page,
  }) => {
    let releaseUpload!: () => void;
    const uploadCanFinish = new Promise<void>((resolve) => {
      releaseUpload = resolve;
    });
    let uploadStarted!: () => void;
    const uploadStartedPromise = new Promise<void>((resolve) => {
      uploadStarted = resolve;
    });

    await page.route("**/api/threads/*/uploads", async (route) => {
      uploadStarted();
      await uploadCanFinish;
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          success: true,
          message: "Uploaded",
          files: [
            {
              filename: "report.docx",
              size: 12,
              path: "report.docx",
              virtual_path: "/mnt/user-data/uploads/report.docx",
              artifact_url: "/api/threads/test/uploads/report.docx",
              extension: ".docx",
            },
          ],
        }),
      });
    });

    await page.goto("/workspace/chats/new");

    const textarea = page.getByPlaceholder(/how can i assist you/i);
    await expect(textarea).toBeVisible({ timeout: 15_000 });
    const promptForm = page.locator("form").filter({ has: textarea });

    await page.getByLabel("Upload files").setInputFiles({
      name: "report.docx",
      mimeType:
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
      buffer: Buffer.from("fake docx"),
    });
    await expect(promptForm.getByText("report.docx")).toBeVisible();

    await textarea.fill("Summarize this document");
    await textarea.press("Enter");

    await uploadStartedPromise;
    await expect(promptForm.getByText("report.docx")).toBeVisible();

    releaseUpload();
    await expect(page.getByText("Hello from GVIM AI!")).toBeVisible({
      timeout: 10_000,
    });
    await expect(promptForm.getByText("report.docx")).toBeHidden();
  });

  test("keeps many attachments in one row without hiding prompt text", async ({
    page,
  }) => {
    await page.goto("/workspace/chats/new");

    const textarea = page.getByPlaceholder(/how can i assist you/i);
    await expect(textarea).toBeVisible({ timeout: 15_000 });
    const promptForm = page.locator("form").filter({ has: textarea });
    const attachmentStrip = promptForm.locator(
      "[data-prompt-input-attachments]",
    );
    const prompt =
      "The first line must remain visible after uploading several files.\n" +
      "Continue with the full analysis using every attachment.";

    await textarea.fill(prompt);
    await page.getByLabel("Upload files").setInputFiles(
      Array.from({ length: 8 }, (_, index) => ({
        name: `long-input-layout-regression-file-${index + 1}.txt`,
        mimeType: "text/plain",
        buffer: Buffer.from(`file ${index + 1}`),
      })),
    );

    await expect(attachmentStrip).toBeVisible();
    await expect(textarea).toHaveValue(prompt);

    const layout = await attachmentStrip.evaluate((element) => {
      const stripRect = element.getBoundingClientRect();
      const itemTops = Array.from(element.children).map(
        (child) => child.getBoundingClientRect().top,
      );
      const textarea = element.parentElement?.querySelector(
        'textarea[name="message"]',
      );
      const textareaRect = textarea?.getBoundingClientRect();

      return {
        itemRows: new Set(itemTops).size,
        scrollWidth: element.scrollWidth,
        clientWidth: element.clientWidth,
        stripBottom: stripRect.bottom,
        textareaTop: textareaRect?.top ?? 0,
      };
    });

    expect(layout.itemRows).toBe(1);
    expect(layout.scrollWidth).toBeGreaterThan(layout.clientWidth);
    expect(layout.textareaTop).toBeGreaterThanOrEqual(layout.stripBottom);
  });
});
