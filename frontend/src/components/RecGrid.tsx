import type { ScoredMovie } from "../api";
import { MovieCard } from "./MovieCard";

export function RecGrid({ items, onPick }: { items: ScoredMovie[]; onPick: (id: number) => void }) {
  if (items.length === 0) return <p className="text-sm text-slate-500">Рекомендаций пока нет.</p>;
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
      {items.map((m) => (
        <MovieCard key={m.id} movie={m} score={m.score} onClick={() => onPick(m.id)} />
      ))}
    </div>
  );
}
