import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { resolve } from "path";
import { fileURLToPath } from "url";

const projectRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  plugins: [vue()],
  root: resolve(projectRoot),
  build: {
    outDir: resolve(projectRoot, "../static"),
    emptyOutDir: true,
    rollupOptions: {
      input: {
        chat: resolve(projectRoot, "chat.html"),
        admin: resolve(projectRoot, "admin.html"),
        vectors: resolve(projectRoot, "vectors.html"),
      },
    },
  },
});
