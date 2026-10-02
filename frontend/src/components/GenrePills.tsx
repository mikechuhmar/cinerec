import { translateGenre } from "../lib/labels";

export function GenrePills({ genres }: { genres: string[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {genres.slice(0, 4).map((g) => (
        <span
          key={g}
          className="rounded-full border border-indigo-400/20 bg-indigo-500/10 px-2 py-0.5 text-[11px] font-medium text-indigo-200"
        >
          {translateGenre(g)}
        </span>
      ))}
    </div>
  );
}
