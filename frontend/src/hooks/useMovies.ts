import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  addRating,
  getGenres,
  getMovie,
  getSimilar,
  getUserRatings,
  getUserRecs,
  searchMovies,
  type CatalogQuery,
  type SimilarMethod,
  type UserMethod,
} from "../api";

export const PAGE_SIZE = 12;

type CatalogFilters = Pick<CatalogQuery, "q" | "genre" | "sort">;

export function useGenres() {
  return useQuery({ queryKey: ["genres"], queryFn: getGenres });
}

export function useMovies(filters: CatalogFilters) {
  return useInfiniteQuery({
    queryKey: ["movies", filters],
    queryFn: ({ pageParam = 0 }) =>
      searchMovies({ ...filters, limit: PAGE_SIZE, offset: pageParam }),
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      const next = lastPage.offset + lastPage.limit;
      return next < lastPage.total ? next : undefined;
    },
  });
}

export function useMovie(id: number | null) {
  return useQuery({
    queryKey: ["movie", id],
    queryFn: () => getMovie(id as number),
    enabled: id != null,
  });
}

export function useSimilar(id: number | null, method: SimilarMethod) {
  return useQuery({
    queryKey: ["similar", id, method],
    queryFn: () => getSimilar(id as number, method),
    enabled: id != null,
  });
}

export function useUserRecs(userId: number, method: UserMethod, enabled: boolean) {
  return useQuery({
    queryKey: ["userRecs", userId, method],
    queryFn: () => getUserRecs(userId, method),
    enabled,
  });
}

export function useUserRatings(userId: number) {
  return useQuery({
    queryKey: ["userRatings", userId],
    queryFn: () => getUserRatings(userId),
  });
}

export function useAddRating(userId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (vars: { movieId: number; rating: number }) =>
      addRating(userId, vars.movieId, vars.rating),
    onSuccess: (_data, vars) => {
      // New rating changes movie stats, recommendations and the user's rating list.
      qc.invalidateQueries({ queryKey: ["movie", vars.movieId] });
      qc.invalidateQueries({ queryKey: ["similar"] });
      qc.invalidateQueries({ queryKey: ["userRecs"] });
      qc.invalidateQueries({ queryKey: ["userRatings", userId] });
      qc.invalidateQueries({ queryKey: ["movies"] });
    },
  });
}
