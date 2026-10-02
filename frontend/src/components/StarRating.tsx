import { useState } from "react";

export function StarRating({ onRate }: { onRate: (value: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex items-center gap-1.5">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onRate(n)}
          className={`text-2xl leading-none transition-transform duration-150 hover:scale-125 ${
            n <= hover
              ? "text-amber-300 drop-shadow-[0_0_6px_rgba(252,211,77,0.5)]"
              : "text-slate-600"
          }`}
          aria-label={`Оценить на ${n}`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
