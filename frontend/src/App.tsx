import { useCallback, useEffect, useState } from "react";
import {
  addRating,
  getGenres,
  getMovie,
  getSimilar,
  getUserRecs,
  searchMovies,
  type Movie,
  type MovieDetail,
  type ScoredMovie,
  type SimilarMethod,
} from "./api";

const PAGE_SIZE = 12;

function Poster({ url, title }: { url: string | null; title: string }) {
  if (!url)
    return (
      <div className="flex aspect-[2/3] w-full items-center justify-center rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 text-3xl">
        🎬
      </div>
    );
  return (
    <img
      src={url}
      alt={title}
      loading="lazy"
      className="aspect-[2/3] w-full rounded-lg object-cover"
    />
  );
}

function GenrePills({ genres }: { genres: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {genres.slice(0, 4).map((g) => (
        <span key={g} className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-xs text-indigo-300">
          {g}
        </span>
      ))}
    </div>
  );
}

function MovieCard({
  movie,
  score,
  onClick,
}: {
  movie: Movie;
  score?: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex flex-col gap-2 rounded-xl border border-white/10 bg-white/5 p-3 text-left transition hover:border-indigo-400/60 hover:bg-white/10"
    >
      <Poster url={movie.poster_url} title={movie.title} />
      <div className="flex items-start justify-between gap-2">
        <span className="text-sm font-medium leading-tight text-white">{movie.title}</span>
        {movie.year && <span className="text-xs text-slate-400">{movie.year}</span>}
      </div>
      <GenrePills genres={movie.genres} />
      <div className="flex items-center justify-between text-xs">
        <span className="text-amber-400">
          {movie.avg_rating ? `★ ${movie.avg_rating}` : "—"}
          {movie.num_ratings > 0 && <span className="text-slate-500"> ({movie.num_ratings})</span>}
        </span>
        {score !== undefined && (
          <span className="font-semibold text-emerald-400">{score.toFixed(3)}</span>
        )}
      </div>
    </button>
  );
}

function RecGrid({ items, onPick }: { items: ScoredMovie[]; onPick: (id: number) => void }) {
  if (items.length === 0)
    return <p className="text-sm text-slate-500">No recommendations available.</p>;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((m) => (
        <MovieCard key={m.id} movie={m} score={m.score} onClick={() => onPick(m.id)} />
      ))}
    </div>
  );
}

function StarRating({ onRate }: { onRate: (value: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onRate(n)}
          className={`text-2xl leading-none transition ${
            n <= hover ? "text-amber-300" : "text-slate-600 hover:text-amber-200"
          }`}
          aria-label={`Rate ${n} stars`}
        >
          ★
        </button>
      ))}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [genre, setGenre] = useState("");
  const [sort, setSort] = useState("popularity");
  const [genres, setGenres] = useState<string[]>([]);
  const [movies, setMovies] = useState<Movie[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  const [selected, setSelected] = useState<MovieDetail | null>(null);
  const [simMethod, setSimMethod] = useState<SimilarMethod>("hybrid");
  const [recs, setRecs] = useState<ScoredMovie[]>([]);
  const [userId, setUserId] = useState(1);
  const [userRecs, setUserRecs] = useState<ScoredMovie[]>([]);
  const [toast, setToast] = useState("");

  useEffect(() => {
    getGenres().then(setGenres).catch(console.error);
  }, []);

  const load = useCallback(
    async (reset: boolean) => {
      const nextOffset = reset ? 0 : offset;
      const page = await searchMovies({
        q: query,
        genre: genre || undefined,
        sort,
        limit: PAGE_SIZE,
        offset: nextOffset,
      });
      setTotal(page.total);
      setOffset(nextOffset + PAGE_SIZE);
      setMovies((prev) => (reset ? page.items : [...prev, ...page.items]));
    },
    [query, genre, sort, offset],
  );

  useEffect(() => {
    load(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [genre, sort]);

  const loadSimilar = useCallback(async (id: number, method: SimilarMethod) => {
    const res = await getSimilar(id, method);
    setRecs(res.items);
  }, []);

  const pick = async (id: number) => {
    const detail = await getMovie(id);
    setSelected(detail);
    await loadSimilar(id, simMethod);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const changeMethod = async (method: SimilarMethod) => {
    setSimMethod(method);
    if (selected) await loadSimilar(selected.id, method);
  };

  const rate = async (value: number) => {
    if (!selected) return;
    await addRating(userId, selected.id, value);
    setToast(`Rated "${selected.title}" ${value}★ as user ${userId}`);
    setSelected(await getMovie(selected.id));
    setTimeout(() => setToast(""), 3000);
  };

  const loadUserRecs = async () => {
    const res = await getUserRecs(userId, "hybrid");
    setUserRecs(res.items);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 bg-gradient-to-r from-indigo-900/40 to-slate-950 px-6 py-5">
        <h1 className="text-2xl font-bold tracking-tight">
          🎬 cinerec
          <span className="ml-2 text-sm font-normal text-slate-400">
            movie recommendation engine · pgvector + ALS + hybrid
          </span>
        </h1>
      </header>

      {toast && (
        <div className="fixed right-4 top-4 z-50 rounded-lg bg-emerald-600 px-4 py-2 text-sm shadow-lg">
          {toast}
        </div>
      )}

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 p-6 lg:grid-cols-[1.3fr_1fr]">
        <section>
          <form
            onSubmit={(e) => {
              e.preventDefault();
              load(true);
            }}
            className="mb-3 flex flex-wrap gap-2"
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search movies…"
              className="min-w-40 flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-indigo-400"
            />
            <select
              value={genre}
              onChange={(e) => setGenre(e.target.value)}
              className="rounded-lg border border-white/10 bg-slate-900 px-3 py-2"
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
            <span>{total} movies</span>
          </div>

          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {movies.map((m) => (
              <MovieCard key={m.id} movie={m} onClick={() => pick(m.id)} />
            ))}
          </div>

          {movies.length < total && (
            <div className="mt-4 text-center">
              <button
                onClick={() => load(false)}
                className="rounded-lg border border-white/15 bg-white/5 px-5 py-2 text-sm hover:bg-white/10"
              >
                Load more
              </button>
            </div>
          )}
        </section>

        <section className="lg:sticky lg:top-6 lg:h-fit">
          <div className="mb-5 rounded-xl border border-white/10 bg-white/5 p-4">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              Recommendations for a user (hybrid)
            </h2>
            <div className="flex items-center gap-2">
              <span className="text-sm text-slate-400">user id</span>
              <input
                type="number"
                min={1}
                value={userId}
                onChange={(e) => setUserId(Number(e.target.value))}
                className="w-24 rounded-lg border border-white/10 bg-white/5 px-2 py-1"
              />
              <button
                onClick={loadUserRecs}
                className="rounded-lg bg-emerald-600 px-3 py-1 text-sm font-medium hover:bg-emerald-500"
              >
                Recommend
              </button>
            </div>
            {userRecs.length > 0 && (
              <div className="mt-3">
                <RecGrid items={userRecs} onPick={pick} />
              </div>
            )}
          </div>

          {!selected ? (
            <div className="rounded-xl border border-dashed border-white/15 p-10 text-center text-slate-500">
              Select a movie to see details and similar titles.
            </div>
          ) : (
            <div>
              <div className="flex gap-4 rounded-xl border border-white/10 bg-white/5 p-5">
                <div className="w-28 shrink-0">
                  <Poster url={selected.poster_url} title={selected.title} />
                </div>
                <div className="flex-1">
                  <h2 className="text-xl font-bold">
                    {selected.title}{" "}
                    {selected.year && <span className="text-slate-400">({selected.year})</span>}
                  </h2>
                  <div className="mt-2">
                    <GenrePills genres={selected.genres} />
                  </div>
                  <p className="mt-2 text-sm text-slate-300">
                    ⭐ {selected.avg_rating ?? "—"} · {selected.num_ratings} ratings
                  </p>
                  {selected.overview && (
                    <p className="mt-2 line-clamp-3 text-xs text-slate-400">{selected.overview}</p>
                  )}
                  <div className="mt-3">
                    <span className="mb-1 block text-xs text-slate-400">
                      Rate as user {userId}:
                    </span>
                    <StarRating onRate={rate} />
                  </div>
                </div>
              </div>

              <div className="mt-5">
                <div className="mb-3 flex items-center gap-2">
                  <h3 className="font-semibold text-indigo-300">Similar movies</h3>
                  <div className="flex gap-1 rounded-lg bg-white/5 p-1 text-xs">
                    {(["hybrid", "content", "collaborative"] as SimilarMethod[]).map((m) => (
                      <button
                        key={m}
                        onClick={() => changeMethod(m)}
                        className={`rounded px-2 py-1 capitalize transition ${
                          simMethod === m ? "bg-indigo-600 text-white" : "text-slate-400"
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
                <RecGrid items={recs} onPick={pick} />
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
