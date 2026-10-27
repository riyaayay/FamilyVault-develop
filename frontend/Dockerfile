FROM node:20-alpine
WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 1111
CMD ["npm", "run", "dev", "--", "-p", "1111", "-H", "0.0.0.0"]
