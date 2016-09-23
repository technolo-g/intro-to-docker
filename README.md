# Intro to Docker


# Commands
```
# Build images
docker build -t butlercam/python-base images/python-base
docker build -t butlercam/flask-app images/flask-app
docker build -t butlercam/redis-server images/redis-server

# Dev mode
docker-compose -f compose/compose-development.yml up

# Prod mode
docker-compose -f compose/compose-production.yml up -d
```

# TODO:
- Dont load almci

