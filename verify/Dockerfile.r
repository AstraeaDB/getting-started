# R lesson image. r-base carries R; the astraeadb binary is copied from the
# base image rather than rebuilt, which would cost another three minutes.
FROM r-base:latest

ENV DEBIAN_FRONTEND=noninteractive
USER root
RUN apt-get update && apt-get install -y \
      libcurl4-openssl-dev libssl-dev libxml2-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# The binary is extracted from astraea-verify-base into the build context by
# build_images.py. COPY --from=<local image> does not work here: buildkit
# treats the name as a registry reference and tries to pull it from Docker Hub.
COPY bin/astraeadb /usr/local/bin/astraeadb
COPY server.toml /etc/astraeadb/server.toml

# Q1: the CRAN package 404s today, so install_github is the instruction the R
# lessons actually print. Revisit when the CRAN submission lands.
RUN R -e 'install.packages("remotes", repos="https://cloud.r-project.org")' \
 && R -e 'remotes::install_github("AstraeaDB/R-AstraeaDB")'

RUN astraeadb --version && R -e 'library(AstraeaDB); cat("R client ok\n")'
WORKDIR /work
