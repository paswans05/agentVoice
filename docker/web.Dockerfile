FROM node:22-alpine

WORKDIR /app

COPY package.json ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/config/package.json ./packages/config/package.json
COPY packages/shared-types/package.json ./packages/shared-types/package.json
COPY packages/ui/package.json ./packages/ui/package.json

RUN npm install

COPY packages ./packages
COPY apps/web ./apps/web

EXPOSE 3000

CMD ["npm", "--workspace=@agentvoice/web", "run", "dev", "--", "-H", "0.0.0.0"]
