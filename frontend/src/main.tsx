import React from "react";
import ReactDOM from "react-dom/client";
import { Toaster } from "sonner";

import App from "./App";
import { AppProviders } from "./app/providers";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <AppProviders>
      <App />
      <Toaster
        richColors
        toastOptions={{
          style: {
            background: "#121720",
            border: "1px solid rgba(30,169,255,0.42)",
            color: "#eff6ff"
          }
        }}
      />
    </AppProviders>
  </React.StrictMode>
);
