FROM ubuntu:xenial
MAINTAINER matt@notevenremotelydorky.com
#IMAGE bultercam/redis-server

RUN apt-get update \
    && apt-get install -y redis-server \
    && apt-get clean

EXPOSE 6379

ENTRYPOINT  ["/usr/bin/redis-server"]

