import type { ApiErrorView } from "./contracts";

export class DemoApiError extends Error {
  constructor(readonly detail: ApiErrorView) {
    super(detail.message);
  }
}

export async function demoRequest<T extends object>(url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method: body === undefined ? "GET" : "POST",
    headers: body === undefined ? undefined : { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const result = (await response.json()) as T | ApiErrorView;
  if (!response.ok || ("ok" in result && result.ok === false)) {
    throw new DemoApiError(result as ApiErrorView);
  }
  return result as T;
}
