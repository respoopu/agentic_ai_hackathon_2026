import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import type {
  ApiErrorView,
  AttendanceStepResponse,
  DemoAttendanceRequest,
} from "@/lib/contracts";
import { callHobbi, HobbiBackendError, TEEN_TOKEN_COOKIE } from "@/lib/hobbi-server";
import { readJson, routeError } from "@/lib/route-response";

export async function POST(
  request: Request,
): Promise<NextResponse<AttendanceStepResponse | ApiErrorView>> {
  try {
    const body = await readJson<DemoAttendanceRequest>(request);
    const token = (await cookies()).get(TEEN_TOKEN_COOKIE)?.value;
    if (!token) {
      throw new HobbiBackendError(
        "demo_session_expired",
        "This demo session has ended. Start a new try.",
        401,
      );
    }
    const now = new Date().toISOString();
    const result = await callHobbi(
      {
        operation: "attendance",
        teen_id: body.teen_id,
        event: {
          booking_id: body.booking_id,
          attended: body.attended,
          occurred_at: now,
        },
        ...(body.debrief
          ? {
              debrief: {
                booking_id: body.booking_id,
                text: body.debrief,
                channel: "in_app",
                submitted_at: now,
              },
            }
          : {}),
      },
      token,
    );
    return NextResponse.json({
      ok: true,
      adaptation: result.adaptation as AttendanceStepResponse["adaptation"],
    });
  } catch (error) {
    return routeError(error);
  }
}
