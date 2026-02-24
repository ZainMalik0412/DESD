# build dependencies and packages stag
FROM python:3.12-alpine AS builder

RUN apk add --no-cache gcc musl-dev postgresql-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# run stage
FROM python:3.12-alpine AS production

RUN apk add --no-cache libpq

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY . .

RUN chmod +x /app/start.sh

RUN mkdir -p /app/staticfiles && \
    addgroup -S django && \
    adduser -S -G django django && \
    chown -R django:django /app

USER django

EXPOSE 8000

ENTRYPOINT ["/app/start.sh"]
CMD ["gunicorn", "brfn_app.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
