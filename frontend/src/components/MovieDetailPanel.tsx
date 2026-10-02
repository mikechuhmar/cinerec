import type { SimilarMethod } from "../api";
import { useMovie, useSimilar } from "../hooks/useMovies";
import { METHOD_RU, pluralRatings } from "../lib/labels";
import { GenrePills } from "./GenrePills";
import { Poster } from "./Poster";
import { RecGrid } from "./RecGrid";
import { StarRating } from "./StarRating";

const METHODS: SimilarMethod[] = ["hybrid", "content", "collaborative"];

export function MovieDetailPanel({
  movieId,
  userId,
  method,
  setMethod,
  onRate,
  onPick,
}: {
  movieId: number | null;
  userId: number;
  method: SimilarMethod;
  setMethod: (m: SimilarMethod) => void;
  onRate: (value: number) => void;
  onPick: (id: number) => void;
}) {
  const movieQuery = useMovie(movieId);
  const similarQuery = useSimilar(movieId, method);
  const movie = movieQuery.data;

  if (movieId == null || !movie)
    return (
      <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.02] p-12 text-center text-slate-500">
        <div className="mb-2 text-4xl">🎞️</div>
        Выберите фильм, чтобы увидеть детали и похожие картины.
      </div>
    );

  return (
    <div className="animate-fade-in-up">
      <div className="flex gap-4 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-lg shadow-slate-950/30 backdrop-blur-sm">
        <div className="group w-28 shrink-0">
          <Poster url={movie.poster_url} title={movie.title} />
        </div>
        <div className="flex-1">
          <h2 className="text-xl font-bold text-white">
            {movie.title} {movie.year && <span className="text-slate-400">({movie.year})</span>}
          </h2>
          <div className="mt-2">
            <GenrePills genres={movie.genres} />
          </div>
          <p className="mt-2 text-sm text-slate-300">
            <span className="text-amber-400">⭐ {movie.avg_rating ?? "—"}</span> ·{" "}
            {pluralRatings(movie.num_ratings)}
          </p>
          {movie.overview && (
            <p className="mt-2 line-clamp-3 text-xs text-slate-400">{movie.overview}</p>
          )}
          <div className="mt-3">
            <span className="mb-1 block text-xs text-slate-400">
              Оценить от пользователя {userId}:
            </span>
            <StarRating onRate={onRate} />
          </div>
        </div>
      </div>

      <div className="mt-5">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <h3 className="font-semibold text-indigo-300">Похожие фильмы</h3>
          <div className="flex gap-1 rounded-xl bg-white/5 p-1 text-xs">
            {METHODS.map((m) => (
              <button
                key={m}
                onClick={() => setMethod(m)}
                className={`rounded-lg px-2.5 py-1 transition ${
                  method === m
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                {METHOD_RU[m]}
              </button>
            ))}
          </div>
        </div>
        <RecGrid items={similarQuery.data?.items ?? []} onPick={onPick} />
      </div>
    </div>
  );
}
