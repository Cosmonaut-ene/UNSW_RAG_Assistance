# Multi-stage build for Vue.js frontend
FROM node:20-alpine as build-stage

# Set working directory
WORKDIR /app

# Copy package.json only (exclude package-lock.json via .dockerignore)
COPY package.json ./

# Install all dependencies (will generate fresh package-lock.json)
RUN npm install

# Copy source code
COPY . .

# Set Node.js options to fix crypto.hash compatibility
ENV NODE_OPTIONS="--openssl-legacy-provider"

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine as production-stage

# Copy built app to nginx
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Expose port 80
EXPOSE 80

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://localhost:80/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]