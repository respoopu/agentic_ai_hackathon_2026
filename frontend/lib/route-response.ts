import { NextResponse } from "next/server";

import type { ApiErrorView } from "./contracts";
import { HobbiBackendError } from "./hobbi-server";

const MAX_DEMO_REQUEST_BYTES = 64 * 1024;

export async function readJson<T>(request: Request): Promise<T> {
  const contentType = request.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().startsWith("application/json")) {
    throw new HobbiBackendError(
      "unsupported_media_type",
      "This demo only accepts JSON requests.",
      415,
    );
  }

  const declaredLength = Number(request.headers.get("content-length") ?? 0);
  if (Number.isFinite(declaredLength) && declaredLength > MAX_DEMO_REQUEST_BYTES) {
    throw new HobbiBackendError(
      "request_too_large",
      "That response is too long. Shorten it and try again.",
      413,
    );
  }

  const rawBody = await request.text();
  if (new TextEncoder().encode(rawBody).byteLength > MAX_DEMO_REQUEST_BYTES) {
    throw new HobbiBackendError(
      "request_too_large",
      "That response is too long. Shorten it and try again.",
      413,
    );
  }

  try {
    return JSON.parse(rawBody) as T;
  } catch {
    throw new HobbiBackendError(
      "invalid_json",
      "Some details need your attention before we can continue.",
      400,
    );
  }
}

export function routeError(error: unknown): NextResponse<ApiErrorView> {
  if (error instanceof HobbiBackendError) {
    return NextResponse.json(
      {
        ok: false,
        code: error.code,
        message: error.message,
        retryable: error.retryable,
      },
      { status: error.status },
    );
  }
  return NextResponse.json(
    {
      ok: false,
      code: "invalid_request",
      message: "Some details need your attention before we can continue.",
      retryable: false,
    },
    { status: 400 },
  );
}

export function outcomeOf(result: Record<string, unknown>): string {
  const state = result.state;
  if (typeof state !== "object" || state === null || !("outcome" in state)) {
    return "unknown";
  }
  return String(state.outcome);
}
