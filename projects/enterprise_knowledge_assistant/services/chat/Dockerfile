FROM ghcr.io/astral-sh/uv:0.13.4@sha256:9f130421e930bfbdc563c00740466603f8723158e90297d07957c2294640262b AS uv
FROM python:3.12.15-slim-bookworm@sha256:5d9e6adc9abd558bc0ce05f9ab16cef71328916fc9728f6b81e337af86a737e2
COPY --from=uv /uv /usr/local/bin/uv
ENV TIKTOKEN_CACHE_DIR=/opt/tiktoken-cache
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
WORKDIR /app
COPY services/chat/pyproject.toml services/chat/uv.lock ./
RUN uv sync --locked --no-install-project
COPY services/chat/ ./
RUN uv sync --locked && .venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')" && chmod -R a+rX /opt/tiktoken-cache && useradd --uid 10001 --create-home taskify && chown -R taskify:taskify /app
USER taskify
EXPOSE 8000
CMD ["taskify-chat"]
