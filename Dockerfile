FROM runtime-base:v2
COPY entrypoint.sh /
RUN apt-get update
