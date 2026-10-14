FROM node:24-bookworm-slim AS web-build
WORKDIR /app
ARG API_ORIGIN=http://api:8100
ENV API_ORIGIN=$API_ORIGIN
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:24-bookworm-slim AS web
WORKDIR /app
ENV NODE_ENV=production PORT=3200 HOSTNAME=0.0.0.0
COPY --from=web-build --chown=node:node /app/.next/standalone ./
COPY --from=web-build --chown=node:node /app/.next/static ./.next/static
USER node
EXPOSE 3200
CMD ["node", "server.js"]

FROM python:3.13-slim-bookworm AS api
WORKDIR /app
COPY requirements-lock.txt ./
RUN pip install --no-cache-dir -r requirements-lock.txt && useradd --uid 10001 --create-home runner
COPY workbench ./workbench
COPY migrations ./migrations
USER runner
EXPOSE 8100
CMD ["python", "-m", "uvicorn", "workbench.api:app", "--host", "0.0.0.0", "--port", "8100"]
