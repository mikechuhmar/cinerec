import { QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { queryClient } from "./lib/queryClient";
import { CatalogPage } from "./pages/CatalogPage";

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<CatalogPage />} />
          <Route path="/movie/:movieId" element={<CatalogPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
