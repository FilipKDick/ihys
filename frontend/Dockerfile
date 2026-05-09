FROM node:24-bookworm as base
WORKDIR /app

COPY package*.json ./
RUN npm install
COPY . .

FROM base as dev
# This is set in docker-compose for dev
CMD ["npm", "run", "dev"]

FROM base as builder
RUN npm run build

FROM builder as prod
COPY --from=builder /app/.output ./.output
COPY package*.json ./
RUN npm install --omit=dev # Install only production dependencies
# This is the command to run a built Nuxt app
CMD ["node", ".output/server/index.mjs"]