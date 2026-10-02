import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { SimilarMethod } from "../api";
import { CatalogSection } from "../components/CatalogSection";
import { MovieDetailPanel } from "../components/MovieDetailPanel";
import { UserRecsPanel } from "../components/UserRecsPanel";
import { useAddRating, useGenres, useMovies } from "../hooks/useMovies";

export function CatalogPage() {
  const { movieId } = useParams();
  const navigate = useNavigate();
  const selectedId = movieId ? Number(movieId) : null;

  const [q, setQ] = useState("");
  const [submittedQ, setSubmittedQ] = useState("");
  const [genre, setGenre] = useState("");
  const [sort, setSort] = useState("popularity");
  const [userId, setUserId] = useState(1);
  const [method, setMethod] = useState<SimilarMethod>("hybrid");
  const [toast, setToast] = useState("");

  const genresQuery = useGenres();
  const moviesQuery = useMovies({ q: submittedQ, genre: genre || undefined, sort });
  const addRating = useAddRating(userId);

  const pick = (id: number) => {
    navigate(`/movie/${id}`);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const rate = (value: number) => {
    if (selectedId == null) return;
    addRating.mutate(
      { movieId: selectedId, rating: value },
      {
        onSuccess: () => {
          setToast(`Оценка ${value}★ сохранена (пользователь ${userId})`);
          setTimeout(() => setToast(""), 3000);
        },
      },
    );
  };

  return (
    <div className="min-h-screen text-slate-100">
      <header className="sticky top-0 z-40 border-b border-white/10 bg-slate-950/70 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-6 py-4">
          <span className="text-2xl">🎬</span>
          <div>
            <h1 className="bg-gradient-to-r from-indigo-300 via-violet-300 to-fuchsia-300 bg-clip-text text-2xl font-extrabold tracking-tight text-transparent">
              cinerec
            </h1>
            <p className="text-xs text-slate-400">
              Рекомендатель фильмов · pgvector + ALS + гибрид
            </p>
          </div>
        </div>
      </header>

      {toast && (
        <div className="animate-fade-in-up fixed top-20 right-4 z-50 rounded-xl border border-emerald-400/30 bg-emerald-600/90 px-4 py-2.5 text-sm font-medium text-white shadow-xl backdrop-blur">
          {toast}
        </div>
      )}

      <main className="mx-auto grid max-w-7xl grid-cols-1 gap-6 p-6 lg:grid-cols-[1.3fr_1fr]">
        <CatalogSection
          q={q}
          setQ={setQ}
          genre={genre}
          setGenre={setGenre}
          sort={sort}
          setSort={setSort}
          genres={genresQuery.data ?? []}
          query={moviesQuery}
          onSubmit={() => setSubmittedQ(q)}
          onPick={pick}
        />

        <section className="lg:sticky lg:top-24 lg:h-fit">
          <UserRecsPanel userId={userId} setUserId={setUserId} onPick={pick} />
          <MovieDetailPanel
            movieId={selectedId}
            userId={userId}
            method={method}
            setMethod={setMethod}
            onRate={rate}
            onPick={pick}
          />
        </section>
      </main>

      <footer className="mx-auto max-w-7xl px-6 pt-2 pb-8 text-center text-xs text-slate-600">
        Данные: MovieLens · Рекомендации: контент (pgvector) + коллаборативная фильтрация (ALS) +
        гибрид
      </footer>
    </div>
  );
}
