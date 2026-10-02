export function Poster({ url, title }: { url: string | null; title: string }) {
  return (
    <div className="aspect-[2/3] w-full overflow-hidden rounded-xl bg-slate-800/60 ring-1 ring-white/10">
      {url ? (
        <img
          src={url}
          alt={title}
          loading="lazy"
          className="h-full w-full object-cover transition-transform duration-500 ease-out group-hover:scale-105"
        />
      ) : (
        <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-slate-700/70 to-slate-900 text-4xl">
          🎬
        </div>
      )}
    </div>
  );
}
