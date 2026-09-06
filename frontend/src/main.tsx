import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/public-sans";
import { App } from "./app/App";
import { Providers } from "./app/Providers";
import "./app/styles.css";

createRoot(document.getElementById("root")!).render(
    <StrictMode>
        <Providers>
            <App />
        </Providers>
    </StrictMode>,
);
