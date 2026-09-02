import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HobbiDemo } from "./HobbiDemo";

describe("HobbiDemo", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("starts with a skippable cold start and reports catalogue readiness", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        json: async () => ({
          ok: true,
          ready_for_real_planning: true,
          real_activities: 35,
          verified_activities: 20,
        }),
      }),
    );

    render(<HobbiDemo />);

    expect(screen.getByRole("heading", { name: "Find a first try that actually fits." })).toBeInTheDocument();
    expect(screen.getByText("Surprise me is on.")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Move: active and energetic/i }));
    expect(screen.getByText("1 gentle nudge selected.")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("35 real activities ready")).toBeInTheDocument());
  });
});
