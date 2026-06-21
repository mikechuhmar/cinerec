import { useEffect, useState } from "react";
import {
  getMovie,
  getSimilar,
  getUserRecs,
  searchMovies,
  type Movie,
  type MovieDetail,
  type ScoredMovie,
} from "./api";

function GenrePills({ genres }: { genres: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {genres.map((g) => (
        <span
          key={g}
          className="rounded-full bg-indigo-500/15 px-2 py-0.5 text-xs text-indigo-300"
        >
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
      className="flex w-full flex-col gap-2 rounded-xl border border-white/10 bg-white/5 p-4 text-left transition hover:border-indigo-400/60 hover:bg-white/10"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="font-medium text-white">{movie.title}</span>
        {movie.year && <span className="text-sm text-slate-400">{movie.year}</span>}
      </div>
      <GenrePills genres={movie.genres} />
      {score !== undefined && (
        <span className="mt-1 text-xs font-semibold text-emerald-400">
          score {score.toFixed(3)}
        </span>
      )}
    </button>
  );
}

function RecRow({ items, onPick }: { items: ScoredMovie[]; onPick: (id: number) => void }) {
  if (items.length === 0)
    return <p className="text-sm text-slate-500">No recommendations available.</p>;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
      {items.map((m) => (
        <MovieCard key={m.id} movie={m} score={m.score} onClick={() => onPick(m.id)} />
      ))}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState("");
  const [movies, setMovies] = useState<Movie[]>([]);
  const [selected, setSelected] = useState<MovieDetail | null>(null);
  const [contentRecs, setContentRecs] = useState<ScoredMovie[]>([]);
  const [cfRecs, setCfRecs] = useState<ScoredMovie[]>([]);
  const [userId, setUserId] = useState(1);
  const [userRecs, setUserRecs] = useState<ScoredMovie[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    searchMovies("").then(setMovies).catch(console.error);
  }, []);

  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setMovies(await searchMovies(query));
  };

  const pick = async (id: number) => {
    setLoading(true);
    try {
      const [detail, content, cf] = await Promise.all([
        getMovie(id),
        getSimilar(id, "content"),
        getSimilar(id, "collaborative"),
      ]);
      setSelected(detail);
      setContentRecs(content.items);
      setCfRecs(cf.items);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } finally {
      setLoading(false);
    }
  };

  const loadUserRecs = async () => {
    const recs = await getUserRecs(userId, "collaborative");
    setUserRecs(recs.items);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 bg-gradient-to-r from-indigo-900/40 to-slate-950 px-6 py-5">
        <h1 className="text-2xl font-bold tracking-tight">
          🎬 cinerec
          <span className="ml-2 text-sm font-normal text-slate-400">
            movie recommendation engine · pgvector + ALS
          </span>
        </h1>
      </header>

      <main className="mx-auto grid max-w-6xl grid-cols-1 gap-6 p-6 lg:grid-cols-[1fr_1.2fr]">
        <section>
          <form onSubmit={runSearch} className="mb-4 flex gap-2">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search movies…"
              className="flex-1 rounded-lg border border-white/10 bg-white/5 px-3 py-2 outline-none focus:border-indigo-400"
            />
            <button className="rounded-lg bg-indigo-600 px-4 py-2 font-medium hover:bg-indigo-500">
              Search
            </button>
          </form>

          <div className="mb-6 rounded-xl border border-white/10 bg-white/5 p-4">
            <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-400">
              Recommendations for a user (collaborative)
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
                <RecRow items={userRecs} onPick={pick} />
              </div>
            )}
          </div>

          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Catalog
          </h2>
          <div className="grid grid-cols-1 gap-3">
            {movies.map((m) => (
              <MovieCard key={m.id} movie={m} onClick={() => pick(m.id)} />
            ))}
          </div>
        </section>

        <section className="lg:sticky lg:top-6 lg:h-fit">
          {!selected ? (
            <div className="rounded-xl border border-dashed border-white/15 p-10 text-center text-slate-500">
              Select a movie to see similar titles.
            </div>
          ) : (
            <div className={loading ? "opacity-60" : ""}>
              <div className="rounded-xl border border-white/10 bg-white/5 p-5">
                <h2 className="text-xl font-bold">
                  {selected.title}{" "}
                  {selected.year && <span className="text-slate-400">({selected.year})</span>}
                </h2>
                <div className="mt-2">
                  <GenrePills genres={selected.genres} />
                </div>
                <p className="mt-3 text-sm text-slate-300">
                  ⭐ {selected.avg_rating ?? "—"} · {selected.num_ratings} ratings
                  {selected.imdb_id && <> · IMDb {selected.imdb_id}</>}
                </p>
                {selected.tags && (
                  <p className="mt-2 text-xs text-slate-500">tags: {selected.tags}</p>
                )}
              </div>

              <div className="mt-5">
                <h3 className="mb-2 font-semibold text-indigo-300">
                  Similar by content (pgvector embeddings)
                </h3>
                <RecRow items={contentRecs} onPick={pick} />
              </div>

              <div className="mt-5">
                <h3 className="mb-2 font-semibold text-emerald-300">
                  Similar by collaborative filtering (ALS)
                </h3>
                <RecRow items={cfRecs} onPick={pick} />
              </div>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
