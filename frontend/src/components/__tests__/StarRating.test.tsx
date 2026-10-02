import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StarRating } from "../StarRating";

describe("StarRating", () => {
  it("renders five star buttons", () => {
    render(<StarRating onRate={() => {}} />);
    expect(screen.getAllByRole("button")).toHaveLength(5);
  });

  it("calls onRate with the chosen value", async () => {
    const onRate = vi.fn();
    render(<StarRating onRate={onRate} />);
    await userEvent.click(screen.getByLabelText("Rate 4 stars"));
    expect(onRate).toHaveBeenCalledWith(4);
  });
});
