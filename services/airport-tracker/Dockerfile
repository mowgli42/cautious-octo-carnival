FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy go mod files
COPY go.mod ./
RUN go mod download

# Copy source code
COPY . .

# Get dependencies and build the application
RUN go get github.com/gorilla/mux && \
    CGO_ENABLED=0 GOOS=linux go build -o airport-tracker .

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/airport-tracker .

# Copy config directory
COPY --from=builder /app/config /config

EXPOSE 3003

CMD ["./airport-tracker"]

