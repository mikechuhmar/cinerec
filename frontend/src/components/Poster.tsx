export function Poster({ url, title }: { url: string | null; title: string }) {
  if (!url)
    return (
      <div className="flex aspect-[2/3] w-full items-center justify-center rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 text-3xl">
        🎬
      </div>
    );
  return (
    <img
      src={url}
      alt={title}
      loading="lazy"
      className="aspect-[2/3] w-full rounded-lg object-cover"
    />
  );
}
