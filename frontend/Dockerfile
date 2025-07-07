FROM node:24-bookworm as builder
WORKDIR /app

COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM builder as dev
# This is set in docker-compose for dev
CMD ["npm", "run", "dev"]

FROM builder as prod
COPY --from=builder /app/.output ./.output
COPY package*.json ./
RUN npm install --omit=dev # Install only production dependencies
# This is the command to run a built Nuxt app
CMD ["node", ".output/server/index.mjs"]