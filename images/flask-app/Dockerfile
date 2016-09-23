FROM butlercam/python-base:latest
#IMAGE butlercam/flask-app

# Define the config file
ENV BUTLERCAM_SETTINGS_FILE /appenv/rally.cfg

ADD flask /appenv
ADD bin /bin

RUN chown -R appuser.appuser /appenv

USER appuser
WORKDIR /appenv

RUN . /virtualenv/bin/activate \
    && pip install -r requirements.txt

ENTRYPOINT [ "/bin/start_server.sh" ]

