import { useState } from "react";

export function StarRating({ onRate }: { onRate: (value: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex items-center gap-1">
      {[1, 2, 3, 4, 5].map((n) => (
        <button
          key={n}
          onMouseEnter={() => setHover(n)}
          onMouseLeave={() => setHover(0)}
          onClick={() => onRate(n)}
          className={`text-2xl leading-none transition ${
            n <= hover ? "text-amber-300" : "text-slate-600 hover:text-amber-200"
          }`}
          aria-label={`Rate ${n} stars`}
        >
          ★
        </button>
      ))}
    </div>
  );
}
