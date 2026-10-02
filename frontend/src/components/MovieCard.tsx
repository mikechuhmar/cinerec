import type { Movie } from "../api";
import { displayTitle } from "../lib/labels";
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
  const title = displayTitle(movie);
  return (
    <button
      onClick={onClick}
      className="group flex flex-col gap-2.5 rounded-2xl border border-white/10 bg-white/[0.03] p-3 text-left shadow-sm ring-1 ring-transparent transition duration-200 hover:-translate-y-1 hover:border-indigo-400/40 hover:bg-white/[0.06] hover:shadow-xl hover:shadow-indigo-950/40 hover:ring-indigo-400/20"
    >
      <Poster url={movie.poster_url} title={title} />
      <div className="flex items-start justify-between gap-2">
        <span className="line-clamp-2 text-sm leading-tight font-semibold text-white">{title}</span>
        {movie.year && <span className="shrink-0 text-xs text-slate-400">{movie.year}</span>}
      </div>
      <GenrePills genres={movie.genres} />
      <div className="mt-auto flex items-center justify-between pt-1 text-xs">
        <span className="font-medium text-amber-400">
          {movie.avg_rating ? `★ ${movie.avg_rating}` : "— без оценок"}
          {movie.num_ratings > 0 && <span className="text-slate-500"> ({movie.num_ratings})</span>}
        </span>
        {score !== undefined && (
          <span className="rounded-md bg-emerald-500/10 px-1.5 py-0.5 font-semibold text-emerald-300">
            {score.toFixed(3)}
          </span>
        )}
      </div>
    </button>
  );
}
