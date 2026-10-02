import type { Movie } from "../api";
import { GenrePills } from "./GenrePills";
import { Poster } from "./Poster";

export function MovieCard({
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
        <span className="text-sm leading-tight font-medium text-white">{movie.title}</span>
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
