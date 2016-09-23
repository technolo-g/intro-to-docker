# Intro to Docker

This repository contains a working version of Butlercam (forked) for the purpose
of learning about the Docker ecosystem. 

# Workshop
https://gist.github.com/technolo-g/7316f1b197cad199005fb7b2104279bd

# Swarm mode demo
https://gist.github.com/technolo-g/4a566d850237ef38e79d7474a2e98b8d


# Building images
```
# Build the required Docker images
docker build -t butlercam/python-base images/python-base
docker build -t butlercam/flask-app images/flask-app
docker build -t butlercam/redis-server images/redis-server
```

# Running in production mode
```
docker-compose -f compose/docker-compose.yml up -d

# Scale the number of butlercam nodes
docker-compose -f compose/docker-compose.yml scale flask-app=3

# Scale nodes back down
docker-compose -f compose/docker-compose.yml scale flask-app=1
```

# Running in development mode (add the dev mount)
```
docker-compose -f compose/docker-compose.yml -f compose/docker-compose.dev.yml up
```



# Debugging
```
# Look at the logs of the container
docker logs -f compose_flask-app_1

# Exec into the container to poke around
docker exec -ti compose_flask-app_1 bash
```

