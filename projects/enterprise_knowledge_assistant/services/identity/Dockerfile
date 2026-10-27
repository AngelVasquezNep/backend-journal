FROM ghcr.io/astral-sh/uv:0.13.4@sha256:9f130421e930bfbdc563c00740466603f8723158e90297d07957c2294640262b AS uv
FROM python:3.14.8-slim-bookworm@sha256:58b9cb2dde6dc8ca7cabd10942d9d01ead923811b191f259008942f7b402ca7e
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/identity/pyproject.toml services/identity/uv.lock ./
RUN uv sync --locked --no-install-project
COPY services/identity/ ./
RUN uv sync --locked && useradd --uid 10001 --create-home taskify && chown -R taskify:taskify /app
USER taskify
EXPOSE 8000
CMD ["taskify-identity"]
