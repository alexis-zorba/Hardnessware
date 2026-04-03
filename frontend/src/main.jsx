import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const rootElement = document.getElementById("root");
const bootElement = document.getElementById("boot-status");

function setBootStatus(message) {
  if (bootElement) {
    bootElement.textContent = message;
  }
}

if (!rootElement) {
  document.body.innerHTML = "<pre style='color:#fff;background:#111;padding:12px'>HARDNESS bootstrap error: #root non trovato.</pre>";
} else {
  setBootStatus("Caricamento Workbench...");
  import("./App.jsx")
    .then(({ App }) => {
      createRoot(rootElement).render(
        <React.StrictMode>
          <App />
        </React.StrictMode>
      );
      setBootStatus("");
    })
    .catch((err) => {
      setBootStatus(`Errore bootstrap frontend: ${String(err)}`);
      rootElement.innerHTML = "<pre style='color:#fff;background:#2a1111;border:1px solid #7a2222;padding:12px'>Frontend bootstrap failed. Apri DevTools Console.</pre>";
      // eslint-disable-next-line no-console
      console.error(err);
    });
}
