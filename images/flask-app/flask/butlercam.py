"""
An application to monitor pipelines in multiple Jenkins instances
"""
# pylint: disable=C0103

import json
import os
import urllib2
import datetime
import threading
import copy
import ssl
from collections import OrderedDict, defaultdict
from flask import Flask
from flask import render_template, send_from_directory
from walrus import Database

from custom_charts import percentage_chart, buildtime_chart, \
    failure_chart, get_percentages, week_chart
from jenkins_persistence import get_all_builds
import default_settings

# Instantiate our app
app = Flask(__name__)

# Configure our app
app.config.from_object(default_settings)
if 'BUTLERCAM_SETTINGS_FILE' in os.environ:
    app.config.from_envvar('BUTLERCAM_SETTINGS_FILE')
PIPELINES = app.config['PIPELINES']
CSV_DIRECTORY = 'csvs'

# Setup the Redis cache
db = Database(host=app.config['REDIS_HOST'], db=0)
cache = db.cache(default_timeout=app.config['CACHE_TIMEOUT'])

# These are used to control the automatic build updating. As long as `continuous`
# is true, `get_all_builds` will be run every `WAIT_S` seconds to update the Redis
# database with any new builds that may have been added since the last update.
WAIT_S = 300 if ("UPDATE_INTERVAL_S" not in app.config.keys()) else app.config["UPDATE_INTERVAL_S"]
continuous = True

# Home
@app.route("/")
def show_home():
    """
    Displays configured pipeline lights on "/"
    """

    return render_template("index.html", build_lights=get_build_lights())


# Pipelines
@app.route("/pipeline/<pipeline>")
def show_pipeline(pipeline):
    """
    Shows the pipelines dashboard
    """

    pipeline = str(pipeline)
    all_builds = get_all_builds(pipeline)
    overall_earliest = \
        datetime.datetime.fromtimestamp(\
        all_builds[all_builds.keys()[0]]['timestamp'] / 1000)\
        .strftime("%A, %d %b %Y, at %H:%M:%S")
    time_data = get_time_data(all_builds)
    w_c = week_chart(time_data)

    top_failing_jobs = get_top_failing_jobs(all_builds, pipeline)
    latest_build_status = get_latest_build_status(PIPELINES[pipeline][1])

    building = False

    if latest_build_status['building']:
        latest_build_status = get_last_complete_status(PIPELINES[pipeline][1])
        building = True

    latest_keys = all_builds.keys()[-20:]
    latest_builds = OrderedDict()
    for i in latest_keys:
        latest_builds[i] = all_builds[i]

    return render_template('pipeline.html',
                           builds=latest_builds,
                           pipeline=pipeline,
                           pipeline_info=PIPELINES[pipeline],
                           building=building,
                           latest_build_status=latest_build_status,
                           passing_percent=get_percentages(all_builds)[0],
                           overall_earliest=overall_earliest,
                           buildtime_chart=buildtime_chart(latest_builds, pipeline),
                           top_failing_jobs=top_failing_jobs,
                           top_failures_chart=failure_chart(top_failing_jobs),
                           percentage_chart=percentage_chart(all_builds),
                           time_data=time_data,
                           week_chart=w_c)

# Builds
@app.route("/pipeline/<pipeline>/<build_number>")
def show_build(pipeline, build_number):
    """
    TODO
    Shows information about a specific run of the pipeline
    """

    builds = get_all_builds(pipeline)
    build_info = get_build_info(PIPELINES[pipeline][1] + "/" + str(build_number))

    return render_template("build.html",
                           build=build_info,
                           builds=builds,
                           pipeline=pipeline)

# The downloadable CSV data for a pipeline.
@app.route("/pipeline/<pipeline>/csv")
def serve_csv(pipeline):
    """
    Serves a CSV file containing all of the known builds for the pipeline.
    """

    pipeline = str(pipeline)
    all_builds = get_all_builds(pipeline)
    csv_data = generate_build_csv(all_builds)

    if not os.path.exists(CSV_DIRECTORY):
        os.makedirs(CSV_DIRECTORY)

    fn = pipeline + "_builds.csv"
    csv_file = open(CSV_DIRECTORY + '/' + fn, "w")
    csv_file.write(csv_data)
    csv_file.close()

    return send_from_directory(CSV_DIRECTORY, fn, as_attachment=True)

# ms Filter
@app.template_filter('ms_to_time')
def ms_to_time(milliseconds):
    """
    Transform milliseconds to 00d:00h:00m:00s
    """

    remainder = milliseconds / 1000
    seconds = remainder % 60
    remainder /= 60
    minutes = remainder % 60
    remainder /= 60
    hours = remainder % 24
    remainder /= 24
    days = remainder

    output = ""

    if days:
        output += str(days) + "d:"
    if hours:
        output += str(hours) + "h:"
    if minutes:
        output += str(minutes) + "m:"
    if seconds:
        output += str(seconds) + "s"

    return output


# Helper functions

def get_top_failing_jobs(builds, pipeline):
    """
    Take a dict of the builds and return an ordered list of the top failures
    """

    failing_builds = []
    failing_jobs = defaultdict(int)

    for _, build_info in builds.iteritems():
        if build_info.get('result') == 'FAILURE':
            failing_builds.append(build_info)

    for build in failing_builds:
        if not build.get('subBuilds'):
            failing_jobs[pipeline] += 1
        else:
            get_build_failure(build, failing_jobs)

    return_list = []
    for name, failures in failing_jobs.iteritems():
        return_list.append((failures, name))

    return sorted(return_list, reverse=True)


def get_build_failure(build, acc):
    """
    Take a dict or a list of builds and an accumulator of a defaultDict then
    find the builds that caused the failure. These are jobs that have
    result = 'FAILURE' and no subBuilds
    """

    # If it's a list, we need to iterate through it
    if isinstance(build, list) and len(build) > 0:
        for potential_failure in build:
            get_build_failure(potential_failure, acc)
    else:
        if build.get('result') == 'FAILURE':
            if build.get("subBuilds"):
                get_build_failure(build.get("subBuilds"), acc)
            elif build.get("build") and build['build'].get('subBuilds'):
                get_build_failure(build['build'].get('subBuilds'), acc)
            else:
                acc[build['jobName']] += 1

    return acc

def get_build_lights():
    """
    Generate a build light status for each of the pipelines and sort by
    system_name, name and return it in a list.
    """

    build_light_status = []
    for name, metadata in PIPELINES.iteritems():
        system_name = metadata[0]
        parsed_current_status = get_latest_build_status(metadata[1])
        parsed_previous_status = get_last_complete_status(metadata[1])

        current_status = parsed_current_status['result']
        current_build_time = ms_to_time(parsed_current_status['duration'])
        building = parsed_current_status['building']

        previous_status = parsed_previous_status['result']

        build_status = (name,
                        current_status,
                        previous_status,
                        building,
                        system_name,
                        current_build_time)

        build_light_status.append(build_status)

    return sorted(build_light_status, key=lambda x: (x[4], x[0]))


def get_latest_build_status(pipeline_url):
    """
    Get the status and result of the latest build.
    """

    url = pipeline_url + "/lastBuild/api/json?tree=result[*],building[*],duration[*]"
    context = ssl._create_unverified_context()
    data = urllib2.urlopen(url, context=context).read()

    return json.loads(data)


def get_last_complete_status(pipeline_url):
    """
    Get the result of the latest completed build (inherently it is complete).
    """

    url = pipeline_url + "/lastCompletedBuild/api/json?tree=result[*],duration[*]"
    context = ssl._create_unverified_context()
    data = urllib2.urlopen(url, context=context).read()

    return json.loads(data)


def get_build_status(build_url):
    """
    Get the status of a single build (SUCCESS, FAILURE, ABORTED)
    """

    return get_build_info(build_url)["result"]


def get_build_info(build_url):
    """
    This function takes a build url and fetches it from Jenkins. If the build is
    not still running, it will insert it into the (Redis) cache for future use.
    """

    url = build_url + '/api/json'
    if cache.get(url):
        return cache.get(url)

    context = ssl._create_unverified_context()
    data = urllib2.urlopen(url, context=context).read()
    parsed = json.loads(data)

    # This will break with non-build requests
    if not parsed['building']:
        cache.set(url, parsed, 0)

    return parsed

def get_time_data(builds):
    """
    This function fetches build data and uses it to calculate how statistics on
    how long the build was passing or failing.
    """

    build_slices = calculate_build_slices(builds)

    return process_time_data(build_slices)

def calculate_build_slices(builds):
    """
    Given a list of builds, will calculate the time slices that they delineate.
    """

    temp_builds = copy.deepcopy(builds)
    build_nums = sorted(temp_builds.keys())

    # Add a temporary build at the end so that the current slice is considered.
    temp_num = build_nums[-1] + 10000
    now_ut = 1000 * (datetime.datetime.now().utcnow() - \
        datetime.datetime.utcfromtimestamp(0)).total_seconds()

    temp_builds[temp_num] = {
        'number': temp_num,
        'timestamp': now_ut,
        'result': 'NULL'
    }

    build_slices = []
    for i in range(0, len(build_nums) - 1):
        curr_num = build_nums[i]
        if temp_builds[curr_num]['result'] != 'SUCCESS' \
              and temp_builds[curr_num]['result'] != 'FAILURE' \
              and curr_num > 0:
            temp_builds[curr_num]['result'] = temp_builds[build_nums[i - 1]]['result']

        add_build_slice(build_slices, \
            temp_builds[curr_num]['timestamp'], \
            temp_builds[build_nums[i + 1]]['timestamp'], \
            temp_builds[curr_num]['result'] \
        )

    return build_slices

def process_time_data(build_slices):
    """
    When given a list of time slices between builds, this calculates general
    statistics for the entire time span.
    """

    timedata = {
        'build_slices': build_slices
    }
    if len(build_slices) > 0:
        timedata['earliest'] = datetime.datetime.fromtimestamp(build_slices[0]['start'])\
            .strftime('%A, %d %b %Y, at %H:%M:%S')

    gts = 0.0
    rts = 0.0
    for build_slice in timedata['build_slices']:
        if build_slice['result'] == 'SUCCESS':
            gts += float(build_slice['duration'])
        elif build_slice['result'] == 'FAILURE':
            rts += float(build_slice['duration'])

    timedata['green'] = calculate_hms(gts)
    timedata['green']['ts'] = gts

    timedata['red'] = calculate_hms(rts)
    timedata['red']['ts'] = rts

    if rts + gts > 0:
        timedata['green']['perc'] = '(%.1f%%)' % \
            (timedata['green']['ts'] / (timedata['green']['ts'] + timedata['red']['ts']) * 100)
        timedata['red']['perc'] = '(%.1f%%)' % \
            (timedata['red']['ts'] / (timedata['green']['ts'] + timedata['red']['ts']) * 100)
    else:
        timedata['green']['perc'] = ''
        timedata['red']['perc'] = ''

    return timedata

def add_build_slice(build_slices, start, end, result):
    """
    Adds a build slice with the given parameters to the given array.
    """

    build_slices.append({
        'start': start / 1000,
        'end': end / 1000,
        'result': result
    })
    build_slices[-1]['duration'] = build_slices[-1]['end'] - build_slices[-1]['start']

def calculate_hms(total_sec):
    """
    Given a number of seconds, calculate the hours, minutes, and seconds.
    """

    total_sec = int(total_sec)
    seconds = total_sec % 60
    total_sec /= 60
    minutes = total_sec % 60
    total_sec /= 60
    hours = total_sec

    formatted = '%dh %dm' % (hours, minutes)

    return {'h': hours, 'm': minutes, 's': seconds, 'formatted': formatted}

def auto_update_builds():
    """
    Runs get_all_builds for every pipeline in PIPELINES, then
    schedules itself to run again later.
    """

    for pipeline in PIPELINES.keys():
        get_all_builds(pipeline)

    if continuous:
        t = threading.Timer(WAIT_S, auto_update_builds)
        t.daemon = True
        t.start()

def generate_build_csv(builds):
    """
    Given a list of builds, output it to a CSV format.
    """

    date_format = '%Y-%m-%d %H:%M:%S'

    out_build_str = 'number,result,start,duration,description\n'
    for k in builds:
        b = builds[k]
        build_desc = ''
        if b['description'] is not None:
            build_desc = ''.join(c for c in b['description'] if 0 < ord(c) < 128)

        out_build_str += '%s,%s,%s,%s,%s\n' % ( \
            b['number'], \
            b['result'], \
            datetime.datetime.fromtimestamp(b['timestamp'] / 1000)\
                .strftime(date_format), \
            b['duration'], \
            build_desc)

    return out_build_str

if __name__ == '__main__':
    auto_update_builds()
    app.run(host='0.0.0.0', debug=True)
    continuous = False
