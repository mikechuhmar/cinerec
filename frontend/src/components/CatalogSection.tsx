import type { UseInfiniteQueryResult } from "@tanstack/react-query";
import type { MoviePage } from "../api";
import { MovieCard } from "./MovieCard";

interface Props {
  q: string;
  setQ: (v: string) => void;
  genre: string;
  setGenre: (v: string) => void;
  sort: string;
  setSort: (v: string) => void;
  genres: string[];
  query: UseInfiniteQueryResult<{ pages: MoviePage[] }, Error>;
  onSubmit: () => void;
  onPick: (id: number) => void;
}

export function CatalogSection({
  q,
  setQ,
  genre,
  setGenre,
  sort,
  setSort,
  genres,
  query,
  onSubmit,
  onPick,
}: Props) {
  const pages = query.data?.pages ?? [];
  const movies = pages.flatMap((p) => p.items);
  const total = pages[0]?.total ?? 0;

  return (
    <section>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="mb-3 flex flex-wrap gap-2"
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search movies…"
          className="min-w-40 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-indigo-400"
        />
        <select
          value={genre}
          onChange={(e) => setGenre(e.target.value)}
          className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2"
          aria-label="Filter by genre"
        >
          <option value="">All genres</option>
          {genres.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2"
          aria-label="Sort movies"
        >
          <option value="popularity">Most rated</option>
          <option value="rating">Top rated</option>
          <option value="year">Newest</option>
          <option value="title">A–Z</option>
        </select>
        <button className="rounded-lg bg-indigo-600 px-4 py-2 font-medium hover:bg-indigo-500">
          Search
        </button>
      </form>

      <div className="mb-3 flex items-center justify-between text-sm text-slate-400">
        <span>{query.isLoading ? "Loading…" : `${total} movies`}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {movies.map((m) => (
          <MovieCard key={m.id} movie={m} onClick={() => onPick(m.id)} />
        ))}
      </div>

      {query.hasNextPage && (
        <div className="mt-4 text-center">
          <button
            onClick={() => query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
            className="rounded-lg border border-white/15 bg-white/5 px-5 py-2 text-sm hover:bg-white/10 disabled:opacity-50"
          >
            {query.isFetchingNextPage ? "Loading…" : "Load more"}
          </button>
        </div>
      )}
    </section>
  );
}
