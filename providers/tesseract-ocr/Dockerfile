FROM ubuntu@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    OMP_NUM_THREADS=1 \
    OMP_THREAD_LIMIT=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        tesseract-ocr=5.3.4-1build5 \
        tesseract-ocr-eng=1:4.1.0-2 \
    && python3 -m pip install --break-system-packages --no-cache-dir Pillow==12.3.0 \
    && rm -rf /var/lib/apt/lists/* /root/.cache

USER 65532:65532
WORKDIR /workspace
