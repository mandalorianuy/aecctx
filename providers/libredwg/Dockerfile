FROM ubuntu@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

ARG LIBREDWG_VERSION=0.13.4
ARG LIBREDWG_SHA256=7e153ea4dac4cbf3dc9c50b9ef7a5604e09cdd4c5520bcf8017877bbe1422cd5

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential ca-certificates curl libpcre2-dev libtool pkg-config xz-utils zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL "https://github.com/LibreDWG/libredwg/releases/download/$LIBREDWG_VERSION/libredwg-$LIBREDWG_VERSION.tar.xz" -o /tmp/libredwg.tar.xz \
    && echo "$LIBREDWG_SHA256  /tmp/libredwg.tar.xz" | sha256sum -c - \
    && mkdir /tmp/libredwg \
    && tar -xJf /tmp/libredwg.tar.xz --strip-components=1 -C /tmp/libredwg \
    && cd /tmp/libredwg \
    && ./configure --enable-release --disable-bindings --disable-docs --disable-python --prefix=/opt/libredwg

RUN cd /tmp/libredwg \
    && make -j4 \
    && make -C programs check TESTS=dxf.test \
    && make install

FROM ubuntu@sha256:4fbb8e6a8395de5a7550b33509421a2bafbc0aab6c06ba2cef9ebffbc7092d90

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    LD_LIBRARY_PATH=/opt/libredwg/lib \
    PATH=/opt/libredwg/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpcre2-8-0 python3 zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/libredwg /opt/libredwg

USER 65532:65532
WORKDIR /workspace
