import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { Movie } from "../../api";
import { MovieCard } from "../MovieCard";

const movie: Movie = {
  id: 1,
  title: "The Matrix",
  year: 1999,
  genres: ["Action", "Sci-Fi"],
  poster_url: null,
  avg_rating: 4.2,
  num_ratings: 100,
};

describe("MovieCard", () => {
  it("renders title, year, rating and genres", () => {
    render(<MovieCard movie={movie} onClick={() => {}} />);
    expect(screen.getByText("The Matrix")).toBeInTheDocument();
    expect(screen.getByText("1999")).toBeInTheDocument();
    expect(screen.getByText(/★ 4.2/)).toBeInTheDocument();
    expect(screen.getByText("Sci-Fi")).toBeInTheDocument();
  });

  it("shows the recommendation score when provided", () => {
    render(<MovieCard movie={movie} score={0.8734} onClick={() => {}} />);
    expect(screen.getByText("0.873")).toBeInTheDocument();
  });

  it("fires onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<MovieCard movie={movie} onClick={onClick} />);
    await userEvent.click(screen.getByText("The Matrix"));
    expect(onClick).toHaveBeenCalledOnce();
  });
});
