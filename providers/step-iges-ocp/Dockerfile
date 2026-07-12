FROM ubuntu@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    OMP_NUM_THREADS=1 \
    OMP_THREAD_LIMIT=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /tmp/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libgl1 libx11-6 python3 python3-pip \
    && python3 -m pip install --break-system-packages --no-cache-dir -r /tmp/requirements.txt \
    && rm -rf /var/lib/apt/lists/* /root/.cache /tmp/requirements.txt

USER 65532:65532
WORKDIR /workspace
