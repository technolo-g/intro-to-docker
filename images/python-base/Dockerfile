FROM ubuntu:trusty
MAINTAINER matt@notevenremotelydorky.com
#IMAGE butlercam/python-base

# Add the pypy PPA and it's key
RUN echo "deb http://ppa.launchpad.net/pypy/ppa/ubuntu trusty main" > \
    /etc/apt/sources.list.d/pypy-ppa.list
RUN apt-key adv --keyserver keyserver.ubuntu.com \
                --recv-keys 2862D0785AFACD8C65B23DB0251104D968854915

# Install our dependencies (and only them), then cleanup
RUN apt-get update && apt-get install -qyy \
    -o APT::Install-Recommends=false -o APT::Install-Suggests=false \
    python-virtualenv pypy libffi6 openssl git ssh \
    && apt-get clean

# Add our app's user
RUN useradd -M -u 1000 -d /appenv -s /bin/bash appuser

# Configure virtualenv
RUN virtualenv -p /usr/bin/pypy /virtualenv
RUN . /virtualenv/bin/activate; pip install pip

# Set permissons
RUN chown -R appuser.appuser /virtualenv

