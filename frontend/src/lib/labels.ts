import type { SimilarMethod } from "../api";

// MovieLens genres are stored in English; show Russian labels (unknown values pass through).
const GENRE_RU: Record<string, string> = {
  Action: "Боевик",
  Adventure: "Приключения",
  Animation: "Анимация",
  Children: "Детский",
  "Children's": "Детский",
  Comedy: "Комедия",
  Crime: "Криминал",
  Documentary: "Документальный",
  Drama: "Драма",
  Fantasy: "Фэнтези",
  "Film-Noir": "Нуар",
  Horror: "Ужасы",
  IMAX: "IMAX",
  Musical: "Мюзикл",
  Mystery: "Детектив",
  Romance: "Мелодрама",
  "Sci-Fi": "Фантастика",
  Thriller: "Триллер",
  War: "Военный",
  Western: "Вестерн",
  "(no genres listed)": "Без жанра",
};

export const translateGenre = (genre: string): string => GENRE_RU[genre] ?? genre;

// Prefer the Russian title when available, falling back to the original.
export const displayTitle = (m: { title: string; title_ru?: string | null }): string =>
  m.title_ru || m.title;

export const METHOD_RU: Record<SimilarMethod, string> = {
  hybrid: "Гибрид",
  content: "По содержанию",
  collaborative: "Коллаборативный",
};

// Russian pluralisation for "фильм".
export function pluralMovies(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  let word = "фильмов";
  if (mod10 === 1 && mod100 !== 11) word = "фильм";
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) word = "фильма";
  return `${n} ${word}`;
}

export function pluralRatings(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  let word = "оценок";
  if (mod10 === 1 && mod100 !== 11) word = "оценка";
  else if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) word = "оценки";
  return `${n} ${word}`;
}
