import { randomUUID } from "node:crypto";

import { NextResponse } from "next/server";

import type { ApiErrorView, BookingStepResponse, DemoApproveRequest } from "@/lib/contracts";
import { callHobbi, guardianToken } from "@/lib/hobbi-server";
import { outcomeOf, readJson, routeError } from "@/lib/route-response";

export async function POST(
  request: Request,
): Promise<NextResponse<BookingStepResponse | ApiErrorView>> {
  try {
    const body = await readJson<DemoApproveRequest>(request);
    const providerApprovalIds = Object.fromEntries(
      (body.provider_listing_ids ?? []).map((listingId) => [
        listingId,
        `provider-${randomUUID()}`,
      ]),
    );
    const hasSpendApproval = body.spend_ceiling_sgd !== null;
    const result = await callHobbi(
      {
        operation: "guardian_approve",
        teen_id: body.teen_id,
        plan_id: body.plan_id,
        provider_approval_ids: providerApprovalIds,
        attendance_approval_id: `attendance-${randomUUID()}`,
        ...(hasSpendApproval
          ? {
              spend_approval_id: `spend-${randomUUID()}`,
              spend_ceiling_sgd: body.spend_ceiling_sgd,
            }
          : {}),
      },
      guardianToken(),
    );
    return NextResponse.json({
      ok: true,
      outcome: outcomeOf(result),
      plan: (result.plan_view ?? null) as BookingStepResponse["plan"],
      bookings: (result.bookings ?? []) as BookingStepResponse["bookings"],
    });
  } catch (error) {
    return routeError(error);
  }
}
