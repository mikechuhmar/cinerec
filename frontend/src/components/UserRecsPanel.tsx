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
    <div className="mb-5 rounded-xl border border-white/10 bg-white/5 p-4">
      <h2 className="mb-2 text-sm font-semibold tracking-wide text-slate-400 uppercase">
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
          aria-label="User id"
        />
        <button
          onClick={() => recs.refetch()}
          disabled={recs.isFetching}
          className="rounded-lg bg-emerald-600 px-3 py-1 text-sm font-medium hover:bg-emerald-500 disabled:opacity-50"
        >
          {recs.isFetching ? "…" : "Recommend"}
        </button>
      </div>
      {recs.data && recs.data.items.length > 0 && (
        <div className="mt-3">
          <RecGrid items={recs.data.items} onPick={onPick} />
        </div>
      )}
    </div>
  );
}
