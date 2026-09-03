import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HobbiDemo } from "./HobbiDemo";

describe("HobbiDemo", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("moves from demo login through profile setup to the home screen", async () => {
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

    expect(screen.getByRole("heading", { name: "Log in to Hobbi" })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "maya@hobbi.test" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "hobbi123" } });
    fireEvent.click(screen.getByRole("button", { name: "Log in" }));

    expect(screen.getByRole("heading", { name: "Make Hobbi yours" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Get moving/i }));
    fireEvent.click(screen.getByRole("button", { name: "Save profile" }));

    expect(screen.getByRole("heading", { name: "What should we try?" })).toBeInTheDocument();
    expect(screen.getByText(/Get moving/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("35 activities ready")).toBeInTheDocument());
  });
});
