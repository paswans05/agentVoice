FROM node:22-alpine

WORKDIR /app/agentvoice-phone-web

COPY agentvoice-phone-web/package.json ./
RUN npm install

COPY agentvoice-phone-web ./

EXPOSE 3001

CMD ["npm", "run", "dev", "--", "-H", "0.0.0.0", "-p", "3001"]
