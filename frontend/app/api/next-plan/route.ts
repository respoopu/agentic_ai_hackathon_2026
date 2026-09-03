import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import type { ApiErrorView, DemoNextPlanRequest, PlanStepResponse } from "@/lib/contracts";
import { callHobbi, HobbiBackendError, TEEN_TOKEN_COOKIE } from "@/lib/hobbi-server";
import { outcomeOf, readJson, routeError } from "@/lib/route-response";

export async function POST(
  request: Request,
): Promise<NextResponse<PlanStepResponse | ApiErrorView>> {
  try {
    const body = await readJson<DemoNextPlanRequest>(request);
    const token = (await cookies()).get(TEEN_TOKEN_COOKIE)?.value;
    if (!token) {
      throw new HobbiBackendError(
        "demo_session_expired",
        "This demo session has ended. Start a new try.",
        401,
      );
    }
    const result = await callHobbi(
      { operation: "next_plan", teen_id: body.teen_id },
      token,
    );
    return NextResponse.json({
      ok: true,
      teen_id: body.teen_id,
      outcome: outcomeOf(result),
      plan: (result.plan_view ?? null) as PlanStepResponse["plan"],
      approval_requirements: (result.approval_requirements ??
        null) as PlanStepResponse["approval_requirements"],
    });
  } catch (error) {
    return routeError(error);
  }
}
