import { expect, test } from "@playwright/test";

test("plans, approves, books, observes, and adapts through the real service", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Find a first try that actually fits." })).toBeVisible();
  await expect(page.getByText(/real activities ready/)).toBeVisible();

  await page.getByRole("button", { name: /Plan my first try/ }).click();
  await expect(page.getByRole("heading", { name: "A practical first experiment." })).toBeVisible();
  await expect(page.getByText("Human-verified").or(page.getByText("Adult review needed"))).toBeVisible();

  await page.getByRole("button", { name: /Pass to trusted adult/ }).click();
  await expect(page.getByRole("heading", { name: "Trusted-adult review" })).toBeVisible();
  await page.getByRole("button", { name: /Approve & book in sandbox/ }).click();
  await expect(page.getByRole("heading", { name: "Practice booking confirmed." })).toBeVisible();
  await expect(page.getByText("No real provider was contacted and no payment was made.", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: /Log what happened/ }).click();
  await page.getByRole("button", { name: "Not my thing" }).click();
  await page.getByRole("button", { name: /Save what happened/ }).click();
  await expect(page.getByRole("heading", { name: "A little wiser, not boxed in." })).toBeVisible();
  await expect(page.getByText("permanent labels")).toBeVisible();

  await page.getByRole("button", { name: /See the next experiment/ }).click();
  await expect(page.getByText("Next experiment")).toBeVisible();
  await page.getByRole("button", { name: /Review the next plan/ }).click();
  await expect(page.getByRole("heading", { name: "Trusted-adult review" })).toBeVisible();
});
