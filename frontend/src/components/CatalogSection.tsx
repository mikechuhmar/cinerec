import type { UseInfiniteQueryResult } from "@tanstack/react-query";
import type { MoviePage } from "../api";
import { pluralMovies, translateGenre } from "../lib/labels";
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

const SELECT =
  "rounded-xl border border-white/10 bg-slate-900/80 px-3 py-2.5 text-sm outline-none transition focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30";

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
  // Dedupe by id: when the catalogue shifts between page fetches (e.g. after a new rating
  // invalidates the query), fixed offsets can overlap and yield the same movie twice.
  const movies = Array.from(new Map(pages.flatMap((p) => p.items).map((m) => [m.id, m])).values());
  const total = pages[0]?.total ?? 0;

  return (
    <section>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSubmit();
        }}
        className="mb-4 flex flex-wrap gap-2"
      >
        <div className="relative min-w-40 flex-1">
          <span className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-slate-500">
            🔍
          </span>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Поиск фильмов…"
            className="w-full rounded-xl border border-white/10 bg-white/5 py-2.5 pr-3 pl-9 text-sm transition outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          />
        </div>
        <select
          value={genre}
          onChange={(e) => setGenre(e.target.value)}
          className={SELECT}
          aria-label="Фильтр по жанру"
        >
          <option value="">Все жанры</option>
          {genres.map((g) => (
            <option key={g} value={g}>
              {translateGenre(g)}
            </option>
          ))}
        </select>
        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className={SELECT}
          aria-label="Сортировка"
        >
          <option value="popularity">По популярности</option>
          <option value="rating">По рейтингу</option>
          <option value="year">Сначала новые</option>
          <option value="title">По алфавиту</option>
        </select>
        <button className="rounded-xl bg-gradient-to-r from-indigo-600 to-violet-600 px-5 py-2.5 text-sm font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:from-indigo-500 hover:to-violet-500 active:scale-95">
          Найти
        </button>
      </form>

      <div className="mb-3 flex items-center justify-between text-sm text-slate-400">
        <span>{query.isLoading ? "Загрузка…" : `Найдено: ${pluralMovies(total)}`}</span>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {movies.map((m) => (
          <MovieCard key={m.id} movie={m} onClick={() => onPick(m.id)} />
        ))}
      </div>

      {query.hasNextPage && (
        <div className="mt-5 text-center">
          <button
            onClick={() => query.fetchNextPage()}
            disabled={query.isFetchingNextPage}
            className="rounded-xl border border-white/15 bg-white/5 px-6 py-2.5 text-sm font-medium transition hover:bg-white/10 disabled:opacity-50"
          >
            {query.isFetchingNextPage ? "Загрузка…" : "Показать ещё"}
          </button>
        </div>
      )}
    </section>
  );
}
