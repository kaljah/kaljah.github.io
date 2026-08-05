# Use Node.js 20 slim as base image
FROM node:20-slim

# Create and change to the app directory
WORKDIR /usr/src/app

# Copy package.json
COPY package.json ./

# Install only production dependencies
# Note: we don't copy package-lock.json to avoid platform-specific issues with sqlite3 if it was installed on Windows
RUN npm install --omit=dev

# Copy application source code
COPY . .

# Expose the port the app runs on
EXPOSE 3000

# Start the server using the web script
CMD [ "npm", "run", "start:web" ]
