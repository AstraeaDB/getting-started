# Python lesson image. Inherits the astraeadb binary and the build deps from
# the base, so nothing is compiled twice.
FROM astraea-verify-base

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y python3 python3-pip python3-venv \
    && rm -rf /var/lib/apt/lists/*

# The line the Crawl Python lessons print. Debian bookworm marks its Python as
# externally managed (PEP 668), which a reader on their own machine will not
# hit inside a virtualenv; --break-system-packages is the container-only
# equivalent of the venv a reader would be using.
RUN pip install --no-cache-dir --break-system-packages astraeadb

RUN python3 -c "import astraeadb; print('astraeadb python client', astraeadb.__version__ if hasattr(astraeadb,'__version__') else 'ok')"
