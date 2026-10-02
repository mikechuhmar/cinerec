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
          setToast(`Rated movie ${selectedId} ${value}★ as user ${userId}`);
          setTimeout(() => setToast(""), 3000);
        },
      },
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-white/10 bg-gradient-to-r from-indigo-900/40 to-slate-950 px-6 py-5">
        <h1 className="text-2xl font-bold tracking-tight">
          🎬 cinerec
          <span className="ml-2 text-sm font-normal text-slate-400">
            movie recommendation engine · pgvector + ALS + hybrid
          </span>
        </h1>
      </header>

      {toast && (
        <div className="fixed top-4 right-4 z-50 rounded-lg bg-emerald-600 px-4 py-2 text-sm shadow-lg">
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

        <section className="lg:sticky lg:top-6 lg:h-fit">
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
    </div>
  );
}
