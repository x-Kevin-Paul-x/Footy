FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY frontend/package*.json ./
RUN npm ci

# Copy the rest of the application
COPY frontend/ .

# Build the application
ENV VITE_API_BASE_URL=http://localhost:5001
RUN npm run build

# Production server
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
