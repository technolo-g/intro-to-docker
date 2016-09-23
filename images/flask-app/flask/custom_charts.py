"""
A set of functions that configure the HighCharts objects used in
butlercam-app.
"""

import datetime
import copy

def percentage_chart(builds):
    """
    Configure the chart showing the percentage of builds that succeed,
    fail, or are aborted.
    """

    percentages = get_percentages(builds)
    chart = {
        "backgroundColor": 'rgba(255, 255, 255, 0)',
        "plotBackgroundColor": 'none',
        "height": 170
    }
    tooltip = {
        "pointFormat": '{series.name}: <b>{point.percentage:.1f}%</b>'
    }
    series = [{
        "type": 'pie',
        "name": 'Build Success',
        "shadow": 'false',
        "innerSize": '65%',
        "borderWidth": 2,
        "borderColor": '#F1F3EB',
        "data": [
            {
                "name": 'Passing',
                "color": '#028302',
                "y": percentages[0]
            },
            {
                "name": 'Failing',
                "color": '#8B0000',
                "y": percentages[1]
            },
            {
                "name": 'Aborted',
                "color": '#818181',
                "y": percentages[2]
            }
        ]
    }]
    chart_dict = {
        "chart": chart,
        "tooltip": tooltip,
        "series": series
    }

    return chart_dict

def buildtime_chart(builds, pipeline):
    """
    Configures the large chart that shows the build times for each
    of the known builds.
    """

    build_numbers = []
    for i in builds:
        build_numbers.append(i)

    build_times = []
    for i in builds:
        duration = builds[i]['duration'] / 1000 / 60
        if duration > 60:
            duration = 60
        build_times.append(duration)

    chart = {
        "type": 'bar',
        "backgroundColor": 'rgba(255, 255, 255, 0)',
        "height": 1000
    }
    series = [{
        "name": 'Build Time',
        "data": build_times,
        "tooltip": {
            "valueSuffix": ' min'
        }
    }]
    title = {"text": pipeline + " pipeline build times"}
    x_axis = {
        "categories": build_numbers,
        "labels": {
            "format": 'Build #{value}'
        }
    }
    y_axis = {
        "title": {
            "text": 'Build time (minutes)'
        },
        "labels": {
            "format": '{value} mins'
        },
    }


    chart_dict = {
        "chart": chart,
        "series": series,
        "title": title,
        "xAxis": x_axis,
        "yAxis": y_axis
    }

    return chart_dict

def failure_chart(failure_list):
    """
    Configures the chart that shows the percentages of builds that
    pass, fail, or are aborted.
    """

    data = []
    for number, job_name in failure_list:
        tmp = {
            "name": str(job_name),
            "y": int(number)
        }
        data.append(tmp)

    chart = {
        "backgroundColor": 'rgba(255, 255, 255, 0)',
        "plotBackgroundColor": 'none',
        "color": "#fff",
        "height": 200
    }
    tooltip = {
        "pointFormat": '<b>{point.percentage:.1f}%</b>'
    }
    series = [{
        "type": 'pie',
        "name": 'Top Failures',
        "shadow": 'false',
        "borderWidth": 2,
        "borderColor": '#F1F3EB',
        "data": data
    }]
    legend = {
        "itemStyle": {
            "color": '#FFFFFF'
        }
    }
    chart_dict = {
        "chart": chart,
        "tooltip": tooltip,
        "series": series,
        "legend": legend
    }

    return chart_dict

def get_percentages(builds):
    """
    Calculates the percentages of builds that pass, fail, or are
    aborted.
    """

    passing_builds = 0
    failing_builds = 0
    aborted_builds = 0

    for k in builds:
        build = builds[k]
        if isinstance(build, dict):
            if build['result'] == 'SUCCESS':
                passing_builds += 1
            elif build['result'] == 'FAILURE':
                failing_builds += 1
            else:
                aborted_builds += 1

    total_builds = passing_builds + failing_builds + aborted_builds

    passing_percent = passing_builds * 100 / total_builds
    failing_percent = failing_builds * 100 / total_builds
    aborted_percent = aborted_builds * 100 / total_builds

    return [passing_percent, failing_percent, aborted_percent]

def week_chart(time_data):
    """
    Configures the chart that shows the percentage of time spent red
    and green on each day in the past week.
    """

    colors = ["#00d000", "#c00000"]
    chart = {
        "type": "bar",
        "backgroundColor": 'rgba(255, 255, 255, 0)',
        "plotBackgroundColor": 'none',
        "height": 240
    }
    x_axis = {
        "gridLineWidth": 0,
        "categories": ["6d ago", "5d ago", "4d ago", "3d ago", "2d ago", "yesterday", "today"],
        "labels": {
            "style": {
                "color": "#ffffff"
            }
        }
    }
    plot_options = {
        "series": {
            "stacking": "normal",
            "pointWidth": 10
        }
    }
    legend = {
        "itemStyle": {
            "color": "#ffffff"
        }
    }
    series = get_time_percentages(time_data)
    chart_dict = {
        "colors": colors,
        "chart": chart,
        "xAxis": x_axis,
        "plotOptions": plot_options,
        "legend": legend,
        "series": series
    }
    return chart_dict

def get_time_percentages(time_data):
    """
    Analyzes the given time data to produce percentages of time spent
    red and green on each day in the last week.
    """

    dates = [0, 0, 0, 0, 0, 0, datetime.date.today()]

    diff = datetime.timedelta(days=1)
    for i in reversed(range(0, 6)):
        dates[i] = dates[i + 1] - diff

    green = [0, 0, 0, 0, 0, 0, 0]
    red = [0, 0, 0, 0, 0, 0, 0]

    for build_slice in copy.deepcopy(time_data["build_slices"]):
        start_date = datetime.datetime.fromtimestamp(build_slice["start"]).date()
        end_date = datetime.datetime.fromtimestamp(build_slice["end"]).date()

        if start_date != end_date:
            almost_midnight = datetime.time(23, 59, 59)
            newend = (datetime.datetime.combine(start_date, almost_midnight) - \
                datetime.datetime.fromtimestamp(0)).total_seconds()
            build_slice["extra_duration"] = build_slice["end"] - newend
            build_slice["end"] = newend
            build_slice["duration"] = build_slice["end"] - build_slice["start"]

        build_date = datetime.datetime.fromtimestamp(build_slice["start"]).date()

        for i in range(0, 7):
            if build_date == dates[i]:
                if build_slice["result"] == "SUCCESS":
                    green[i] += build_slice["duration"]
                elif build_slice["result"] == "FAILURE":
                    red[i] += build_slice["duration"]

                if i < 6 and "extra_duration" in build_slice:
                    if build_slice["result"] == "SUCCESS":
                        green[i + 1] += build_slice["extra_duration"]
                    elif build_slice["result"] == "FAILURE":
                        red[i + 1] += build_slice["extra_duration"]

    for i in range(0, 7):
        green_t = float(green[i])
        red_t = float(red[i])
        total = float(green_t + red_t)
        if total > 0:
            green[i] = green_t / total * 100
            red[i] = red_t / total * 100

    return [
        {
            "name": "Passing",
            "data": green
        },
        {
            "name": "Failing",
            "data": red
        }
    ]
