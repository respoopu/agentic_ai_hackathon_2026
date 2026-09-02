import { randomUUID } from "node:crypto";

import { NextResponse } from "next/server";

import type { ApiErrorView, DemoSetupRequest, PlanStepResponse } from "@/lib/contracts";
import { callHobbi, guardianToken, TEEN_TOKEN_COOKIE } from "@/lib/hobbi-server";
import { outcomeOf, readJson, routeError } from "@/lib/route-response";

export async function POST(
  request: Request,
): Promise<NextResponse<PlanStepResponse | ApiErrorView>> {
  try {
    const body = await readJson<DemoSetupRequest>(request);
    const teenId = `demo-${randomUUID()}`;
    const threadId = `setup-${randomUUID()}`;
    const now = new Date().toISOString();
    const consent = (kind: string, grantedBy: "teen" | "trusted_adult") => ({
      consent_id: `consent-${randomUUID()}`,
      teen_id: teenId,
      kind,
      granted: true,
      granted_by: grantedBy,
      recorded_at: now,
    });
    const result = await callHobbi(
      {
        operation: "intake_and_plan",
        setup: {
          teen_id: teenId,
          thread_id: threadId,
          declared_age: body.declared_age,
          request: { goal: body.goal, requested_at: now },
          ledger: {
            money_total_sgd: body.money_total_sgd,
            hours_per_week: body.hours_per_week,
            tries_total: body.tries_total,
          },
          consents: [
            consent("personal_data", "teen"),
            consent("trusted_adult_authority", "trusted_adult"),
            consent("peer_cohort", "teen"),
          ],
          parental_rules: body.parental_rules,
          constraints: {
            max_items: 1,
            max_travel_min: body.max_travel_min,
          },
          cold_start_vibes: body.cold_start_vibes,
        },
      },
      guardianToken(),
    );
    const teenToken = result.teen_access_token;
    if (typeof teenToken !== "string") {
      throw new Error("missing teen session token");
    }
    const response = NextResponse.json({
      ok: true,
      teen_id: teenId,
      outcome: outcomeOf(result),
      plan: (result.plan_view ?? null) as PlanStepResponse["plan"],
      approval_requirements: (result.approval_requirements ??
        null) as PlanStepResponse["approval_requirements"],
    });
    response.cookies.set(TEEN_TOKEN_COOKIE, teenToken, {
      httpOnly: true,
      sameSite: "strict",
      secure: process.env.HOBBI_COOKIE_SECURE === "1",
      path: "/",
      maxAge: 60 * 60 * 8,
    });
    return response;
  } catch (error) {
    return routeError(error);
  }
}
