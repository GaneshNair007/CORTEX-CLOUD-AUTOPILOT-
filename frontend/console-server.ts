import express from "express";
import { createServer } from "node:http";
import path from "node:path";
import { createServer as createViteServer } from "vite";
import "dotenv/config";

async function startServer() {
  const app = express();
  const server = createServer(app);
  const port = Number(process.env.PORT || 3000);
  const backend = (
    process.env.PYTHON_BACKEND_URL || "http://127.0.0.1:8000"
  ).replace(/\/$/, "");
  app.use(express.json({ limit: "1mb" }));
  // Preserve backend status and payload; connection failure is never a success.
  app.all("/api/*", async (req, res) => {
    try {
      const headers: Record<string, string> = {
        Accept: "application/json",
        "Content-Type": "application/json",
      };
      if (req.headers.authorization)
        headers.Authorization = req.headers.authorization;
      if (req.headers["x-api-key"])
        headers["X-API-Key"] = String(req.headers["x-api-key"]);
      const upstream = await fetch(`${backend}${req.originalUrl}`, {
        method: req.method,
        headers,
        body: ["GET", "HEAD"].includes(req.method)
          ? undefined
          : JSON.stringify(req.body ?? {}),
        signal: AbortSignal.timeout(185000),
      });
      res
        .status(upstream.status)
        .setHeader(
          "Content-Type",
          upstream.headers.get("content-type") || "application/json",
        );
      res.send(await upstream.text());
    } catch {
      res
        .status(502)
        .json({
          error:
            "Backend unavailable. Check the configured backend address and server status.",
        });
    }
  });
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: {
        middlewareMode: true,
        hmr: process.env.DISABLE_HMR === "true" ? false : { server },
      },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.resolve(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req, res) =>
      res.sendFile(path.join(distPath, "index.html")),
    );
  }
  server.listen(port, "127.0.0.1", () =>
    console.log(`CORTEX frontend: http://localhost:${port}`),
  );
}
void startServer();
