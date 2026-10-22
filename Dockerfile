# The pardesline MCP server (stdio) with every optional backend.
#
#   docker build -t pardesline-mcp .
#   docker run -i --rm -v pardesline-cache:/home/app/.cache/pardesline pardesline-mcp
#
# Add -v /path/to/data:/data to let the agent scan or export a local folder, and
# -e HF_TOKEN=... only for gated Hugging Face datasets whose terms you accepted.
FROM python:3.12-slim

LABEL io.modelcontextprotocol.server.name="io.github.pardesline/pardesline" \
      org.opencontainers.image.title="pardesline MCP server" \
      org.opencontainers.image.description="3D vision and medical imaging datasets and algorithms for AI agents" \
      org.opencontainers.image.source="https://github.com/pardesline/pardesline" \
      org.opencontainers.image.licenses="Apache-2.0"

# System libraries the Open3D and VTK wheels load at import time, even without a display.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libgl1 libegl1 libgomp1 libglib2.0-0 libxrender1 libx11-6 libusb-1.0-0 libidn2-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml README.md LICENSE NOTICE ./
COPY src ./src
COPY skills ./skills
RUN pip install --no-cache-dir ".[all]" && rm -rf /build

RUN useradd --create-home app && mkdir -p /home/app/.cache/pardesline /data \
    && chown -R app /home/app /data
USER app
WORKDIR /data
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["pardesline", "mcp"]
