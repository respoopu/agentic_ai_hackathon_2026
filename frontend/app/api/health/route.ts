import { NextResponse } from "next/server";

import type { ApiErrorView, HealthView } from "@/lib/contracts";
import { callHobbi } from "@/lib/hobbi-server";
import { routeError } from "@/lib/route-response";

export async function GET(): Promise<NextResponse<HealthView | ApiErrorView>> {
  try {
    const result = await callHobbi({ operation: "health" });
    return NextResponse.json({
      ok: true,
      ready_for_real_planning: Boolean(result.ready_for_real_planning),
      real_activities: Number(result.ckb_usable_real_records ?? 0),
      verified_activities: Number(result.ckb_verified_real_records ?? 0),
    });
  } catch (error) {
    return routeError(error);
  }
}
