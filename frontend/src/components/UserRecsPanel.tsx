import { useUserRecs } from "../hooks/useMovies";
import { RecGrid } from "./RecGrid";

export function UserRecsPanel({
  userId,
  setUserId,
  onPick,
}: {
  userId: number;
  setUserId: (v: number) => void;
  onPick: (id: number) => void;
}) {
  const recs = useUserRecs(userId, "hybrid", false);

  return (
    <div className="mb-5 rounded-2xl border border-white/10 bg-white/[0.04] p-5 shadow-lg shadow-slate-950/30 backdrop-blur-sm">
      <h2 className="mb-3 flex items-center gap-2 text-xs font-semibold tracking-wider text-slate-400 uppercase">
        <span className="text-base">✨</span> Рекомендации для пользователя (гибрид)
      </h2>
      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-400" htmlFor="user-id">
          ID пользователя
        </label>
        <input
          id="user-id"
          type="number"
          min={1}
          value={userId}
          onChange={(e) => setUserId(Number(e.target.value))}
          className="w-24 rounded-xl border border-white/10 bg-white/5 px-3 py-1.5 text-sm transition outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-500/30"
          aria-label="ID пользователя"
        />
        <button
          onClick={() => recs.refetch()}
          disabled={recs.isFetching}
          className="rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-4 py-1.5 text-sm font-semibold text-white shadow-lg shadow-emerald-900/40 transition hover:from-emerald-500 hover:to-teal-500 active:scale-95 disabled:opacity-50"
        >
          {recs.isFetching ? "…" : "Подобрать"}
        </button>
      </div>
      {recs.data && recs.data.items.length > 0 && (
        <div className="mt-4">
          <RecGrid items={recs.data.items} onPick={onPick} />
        </div>
      )}
    </div>
  );
}
