import { expect, test } from "@playwright/test";

test("logs in, sets a profile, books, checks in, and adapts through the real service", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Log in to Hobbi" })).toBeVisible();
  await page.getByLabel("Email").fill("maya@hobbi.test");
  await page.getByLabel("Password").fill("hobbi123");
  await page.getByRole("button", { name: "Log in" }).click();

  await expect(page.getByRole("heading", { name: "Make Hobbi yours" })).toBeVisible();
  await page.getByRole("button", { name: "Get moving" }).click();
  await page.getByRole("button", { name: "Save profile" }).click();
  await expect(page.getByRole("heading", { name: "What should we try?" })).toBeVisible();
  await expect(page.getByText(/activities ready/)).toBeVisible();

  await page.getByRole("button", { name: "Find an activity" }).click();
  await expect(page.getByRole("heading", { name: "Try this next" })).toBeVisible();
  await expect(page.getByText("Human-verified").or(page.getByText("Adult review needed"))).toBeVisible();

  await page.getByRole("button", { name: "Ask my adult" }).click();
  await expect(page.getByRole("heading", { name: "Is this okay?" })).toBeVisible();
  await page.getByRole("button", { name: "Approve as demo adult" }).click();
  await expect(page.getByRole("heading", { name: "Nice, you’re in!" })).toBeVisible();
  await expect(page.getByText("No provider was contacted and no payment was made.")).toBeVisible();

  await page.getByRole("button", { name: "Check in after activity" }).click();
  await expect(page.getByRole("heading", { name: "How did it go?" })).toBeVisible();
  await page.getByRole("button", { name: "Not my thing" }).click();
  await page.getByRole("button", { name: "Save check-in" }).click();
  await expect(page.getByRole("heading", { name: "Got it!" })).toBeVisible();

  await page.getByRole("button", { name: "Find another activity" }).click();
  await expect(page.getByText("Next up")).toBeVisible();
  await page.getByRole("button", { name: "Review activity" }).click();
  await expect(page.getByRole("heading", { name: "Is this okay?" })).toBeVisible();
});
