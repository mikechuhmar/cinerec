export function GenrePills({ genres }: { genres: string[] }) {
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
