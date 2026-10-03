# ---- dev: Vite dev server with hot reload (used by docker-compose.yml) ----
FROM node:22-alpine AS dev
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
EXPOSE 5173
CMD ["npx", "vite", "--host", "0.0.0.0", "--port", "5173"]

# ---- build: static production bundle ----
FROM dev AS build
RUN npm run build

# ---- prod: nginx serves the bundle and proxies /api (docker-compose.prod.yml) ----
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
