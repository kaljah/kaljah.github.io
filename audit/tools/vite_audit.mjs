// Serves the REAL client source on :5190, proxying /api to the isolated audit backend on :5055.
import { pathToFileURL } from "url";
const CLIENT = "C:/Users/samsung/Desktop/H2/new/client";
const { createServer } = await import(pathToFileURL(CLIENT + "/node_modules/vite/dist/node/index.js").href);
const react = (await import(pathToFileURL(CLIENT + "/node_modules/@vitejs/plugin-react/dist/index.js").href)).default;
const server = await createServer({
  root: CLIENT, configFile: false, plugins: [react()],
  server: { host: "127.0.0.1", port: Number(process.env.VITE_PORT || 5190), strictPort: true,
    proxy: { "/api/notifications/stream": { target: "http://127.0.0.1:" + (process.env.API_PORT || 5055), changeOrigin: true },
             "/api": { target: "http://127.0.0.1:" + (process.env.API_PORT || 5055), changeOrigin: true } } },
});
await server.listen(); server.printUrls();
