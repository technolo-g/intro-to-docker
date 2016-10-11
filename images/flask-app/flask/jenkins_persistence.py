"""
A component that queries Jenkins for builds and saves them in a local
Redis database so that they can be accessed even after Jenkins has
stopped holding onto them.
"""
# pylint: disable=C0103

import urllib2
import json
import os
import ssl
from collections import OrderedDict
from flask import Flask
from walrus import Database
import default_settings

app = Flask(__name__)
app.config.from_object(default_settings)
if 'BUTLERCAM_SETTINGS_FILE' in os.environ:
    app.config.from_envvar('BUTLERCAM_SETTINGS_FILE')
PIPELINES = app.config['PIPELINES']

db = Database(host=app.config['REDIS_HOST'], db=0)
cache = db.cache(default_timeout=app.config['CACHE_TIMEOUT'])

def get_all_builds(pipeline):
    """
    Given the name of a pipeline, the saved builds for that pipeline are
    retrieved, Jenkins is queried, and the combined results are returned.
    """

    pref_url = PIPELINES[pipeline][1]
    api_url = pref_url + '/api/json'
    context = ssl._create_unverified_context()
    data = urllib2.urlopen(api_url, context=context).read()
    parsed = json.loads(data)

    builds = get_saved_builds(pipeline)
    print 'Builds for pipeline', pipeline, 'previously saved:', len(builds)

    for build in parsed['builds']:
        builds[build['number']] = get_build_info(build['url'])
    builds = OrderedDict(sorted(builds.iteritems(), key=lambda k: k))

    save_builds(pipeline, builds)
    print 'Builds for pipeline', pipeline, 'after updating:', len(builds)

    return builds


def get_saved_builds(pipeline):
    """
    Given the name of a pipeline, load the saved builds from the local
    Redis database.
    """

    redis_builds = db.Array(pipeline + ':builds')
    saved_builds = OrderedDict()
    for i in range(0, len(redis_builds)):
        curr_build = json.loads(redis_builds[i])
        saved_builds[curr_build['number']] = curr_build
    return saved_builds


def save_builds(pipeline, builds):
    """
    Given the name of a pipeline and a dict of builds, clear the
    existing saved builds for that pipeline and add all of the given
    builds in their place.
    """

    redis_builds = db.Array(pipeline + ':builds')
    clear_saved_builds(pipeline)
    for key in builds:
        redis_builds.append(json.dumps(builds[key]))


def clear_saved_builds(pipeline):
    """
    Given the name of a pipeline, empty the local list of builds
    for that pipeline.
    """

    redis_builds = db.Array(pipeline + ':builds')
    while len(redis_builds) > 0:
        redis_builds.pop()


def get_build_info(build_url):
    """
    Given the base URL of a build, query Jenkins to get more detailed
    data about that build.
    """

    url = build_url + 'api/json'
    if cache.get(url):
        return cache.get(url)

    context = ssl._create_unverified_context()
    data = urllib2.urlopen(url, context=context).read()
    parsed = json.loads(data)

    if not parsed['building']:
        cache.set(url, parsed, 0)

    return parsed
