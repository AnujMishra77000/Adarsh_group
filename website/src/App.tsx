import { Navigate, Route, Routes } from "react-router-dom";

import { PublicHomePage } from "./pages/public/HomePage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<PublicHomePage />} />
      <Route path="/about" element={<PublicHomePage />} />
      <Route path="/centers" element={<PublicHomePage />} />
      <Route path="/collections" element={<PublicHomePage />} />
      <Route path="/contact" element={<PublicHomePage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
