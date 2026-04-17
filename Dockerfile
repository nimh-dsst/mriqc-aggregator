FROM python:3.12-slim

ARG PIXI_VERSION=v0.67.0

RUN python - <<PY
import os
import platform
import stat
import urllib.request

arch_map = {
    "x86_64": "x86_64-unknown-linux-musl",
    "amd64": "x86_64-unknown-linux-musl",
    "aarch64": "aarch64-unknown-linux-musl",
    "arm64": "aarch64-unknown-linux-musl",
}

machine = platform.machine().lower()
try:
    target = arch_map[machine]
except KeyError as exc:
    raise SystemExit(f"Unsupported architecture for pixi: {machine}") from exc

url = (
    f"https://github.com/prefix-dev/pixi/releases/download/"
    f"${PIXI_VERSION}/pixi-{target}"
)
path = "/usr/local/bin/pixi"
with urllib.request.urlopen(url) as response, open(path, "wb") as destination:
    destination.write(response.read())
os.chmod(
    path,
    os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
)
PY

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PIXI_HOME=/root/.pixi
ENV PATH="${PIXI_HOME}/bin:${PATH}"

WORKDIR /app

COPY pixi.toml pyproject.toml README.md /app/
COPY mriqc_aggregator /app/mriqc_aggregator
COPY scripts /app/scripts

RUN pixi install

EXPOSE 8000

CMD ["pixi", "run", "python", "scripts/start_api.py"]
