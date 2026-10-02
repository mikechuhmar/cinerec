import { QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { queryClient } from "../../lib/queryClient";
import { CatalogPage } from "../CatalogPage";

function mockFetch(url: string) {
  if (url.includes("/movies/genres")) {
    return Promise.resolve(new Response(JSON.stringify(["Action", "Comedy"])));
  }
  if (url.includes("/movies")) {
    return Promise.resolve(
      new Response(
        JSON.stringify({
          total: 1,
          limit: 12,
          offset: 0,
          items: [
            {
              id: 1,
              title: "The Matrix",
              year: 1999,
              genres: ["Action"],
              poster_url: null,
              avg_rating: 4.2,
              num_ratings: 100,
            },
          ],
        }),
      ),
    );
  }
  return Promise.resolve(new Response(JSON.stringify({})));
}

describe("CatalogPage", () => {
  beforeEach(() => {
    queryClient.clear();
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => mockFetch(String(input))),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the header and loads movies from the API", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <CatalogPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(screen.getByRole("heading", { name: /cinerec/ })).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText("The Matrix")).toBeInTheDocument());
    expect(screen.getByText("Найдено: 1 фильм")).toBeInTheDocument();
  });
});
