FROM golang:1.25

WORKDIR /app

COPY image_worker_service/go.mod ./
RUN go mod download

COPY image_worker_service/ ./

CMD ["go", "run", "."]