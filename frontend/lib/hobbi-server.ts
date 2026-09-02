import "server-only";

const HOBBI_API_URL = process.env.HOBBI_API_URL ?? "http://127.0.0.1:8080";

export const TEEN_TOKEN_COOKIE = "hobbi_demo_teen_token";

type BackendResponse = Record<string, unknown> & {
  ok?: boolean;
  error?: string;
  action?: string;
};

export class HobbiBackendError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
    readonly retryable = false,
  ) {
    super(message);
  }
}

const safeMessages: Record<string, string> = {
  ApiAuthorizationError: "This demo session is no longer authorised. Start a new try.",
  AuthorizationError: "That approval does not match this plan.",
  PersonalDataError: "We could not find this demo session. Start a new try.",
  RequestTooLargeError: "That response is too long. Shorten it and try again.",
  ValidationError: "Some details need your attention before we can continue.",
  stored_state_conflict: "This demo profile already exists. Start a fresh try.",
  internal_error: "Hobbi hit a temporary problem. Please try again.",
};

export function guardianToken(): string {
  const token = process.env.HOBBI_GUARDIAN_API_TOKEN;
  if (!token) {
    throw new HobbiBackendError(
      "demo_not_configured",
      "The trusted-adult demo key is not configured.",
      503,
    );
  }
  return token;
}

export async function callHobbi(
  payload: Record<string, unknown>,
  authorization?: string,
): Promise<BackendResponse> {
  let response: Response;
  try {
    response = await fetch(HOBBI_API_URL, {
      method: "POST",
      headers: {
        "content-type": "application/json",
        ...(authorization ? { authorization: `Bearer ${authorization}` } : {}),
      },
      body: JSON.stringify(payload),
      cache: "no-store",
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new HobbiBackendError(
      "backend_unavailable",
      "The Hobbi service is not running yet.",
      503,
      true,
    );
  }

  const result = (await response.json()) as BackendResponse;
  if (!response.ok || result.ok === false) {
    const code = typeof result.error === "string" ? result.error : "request_failed";
    throw new HobbiBackendError(
      code,
      safeMessages[code] ?? "Hobbi could not complete that step.",
      response.status >= 400 ? response.status : 400,
      response.status >= 500,
    );
  }
  return result;
}
