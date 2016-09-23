import butlercam
import unittest
import datetime
import json
import collections

from collections import OrderedDict

class butlercamTestCase(unittest.TestCase):

    def setUp(self):
        # butlercam.app.config['REDIS_HOST'] = 'localhost'
        butlercam.app.config['TESTING'] = True
        self.app = butlercam.app.test_client()
        with open('all_builds_test.json') as json_file:
            temp_builds = json.load(json_file)
        self.test_builds = {}
        for k, build in temp_builds.iteritems():
            self.test_builds[int(k)] = build
        self.test_build_slices = butlercam.calculate_build_slices(self.test_builds)

    # def tearDown(self):

    def test_no_config(self):
        rv = self.app.get('/')
        assert 'BUTLERCAM Dashboard' in rv.data

    def test_ms_to_time(self):
        assert butlercam.ms_to_time(1000) == "1s"
        assert butlercam.ms_to_time(5233543) == "1h:27m:13s"
        assert butlercam.ms_to_time(52339832543) == "605d:18h:50m:32s"

    def test_get_top_failing_jobs(self):
        top_failing_jobs = butlercam.get_top_failing_jobs(OrderedDict(self.test_builds), 'churro')
        assert len(top_failing_jobs) == 2
        assert top_failing_jobs[0] == (1, 'job3')
        assert top_failing_jobs[1] == (1, 'job1')

    def test_get_build_failure(self):
        acc = collections.defaultdict(int)
        butlercam.get_build_failure(self.test_builds[self.test_builds.keys()[0]], acc)
        assert 'job3' in acc.keys()
        assert acc['job3'] == 1

    def test_get_build_lights(self):
        assert len(butlercam.get_build_lights()) == len(butlercam.app.config['PIPELINES'])

    def test_calculate_build_slices(self):
        assert len(self.test_build_slices) == 2
        assert self.test_build_slices[0]['duration'] == 1860
        assert self.test_build_slices[0]['start'] == 1473261133
        assert self.test_build_slices[0]['end'] == 1473262993
        assert self.test_build_slices[0]['result'] == 'FAILURE'
        assert self.test_build_slices[1]['duration'] == 2195
        assert self.test_build_slices[1]['start'] == 1473262993
        assert self.test_build_slices[1]['end'] == 1473265188
        assert self.test_build_slices[1]['result'] == 'SUCCESS'

    def test_process_time_data(self):
        time_data = butlercam.process_time_data(self.test_build_slices)
        assert time_data['green']['h'] == 0
        assert time_data['green']['m'] == 36
        assert time_data['green']['s'] == 35
        assert time_data['green']['formatted'] == '0h 36m'
        assert time_data['green']['ts'] == 2195
        assert time_data['green']['perc'] == '(54.1%)'
        assert time_data['red']['h'] == 0
        assert time_data['red']['m'] == 31
        assert time_data['red']['s'] == 0
        assert time_data['red']['formatted'] == '0h 31m'
        assert time_data['red']['ts'] == 1860
        assert time_data['red']['perc'] == '(45.9%)'

    def test_add_build_slice(self):
        build_slices = []
        start = 123456
        end = 7891011
        butlercam.add_build_slice(build_slices, start, end, 'FAILURE')
        assert build_slices[0]['start'] == start / 1000
        assert build_slices[0]['end'] == end / 1000
        assert build_slices[0]['result'] == 'FAILURE'
        assert build_slices[0]['duration'] == end / 1000 - start / 1000

    def test_calculate_hms(self):
        assert self.assert_hms(1, 0, 0, 1)
        assert self.assert_hms(60, 0, 1, 0)
        assert self.assert_hms(3600, 1, 0, 0)
        assert self.assert_hms(105, 0, 1, 45)
        assert self.assert_hms(3720, 1, 2, 0)
        assert self.assert_hms(3599.999, 0, 59, 59)
        assert self.assert_hms(10000, 2, 46, 40)

    def assert_hms(self, total_sec, hours, minutes, seconds):
        hms = butlercam.calculate_hms(total_sec)
        return hms["h"] == hours \
            and hms["m"] == minutes \
            and hms["s"] == seconds

    def test_generate_build_csv(self):
        csv_data = butlercam.generate_build_csv(self.test_builds)
        first_row = csv_data.split('\n')[1].split(',')
        first_build = self.test_builds[self.test_builds.keys()[0]]
        assert int(first_row[0]) == first_build['number']
        assert first_row[1] == first_build['result']
        assert first_row[2] == datetime.datetime\
            .fromtimestamp(first_build['timestamp'] / 1000)\
            .strftime('%Y-%m-%d %H:%M:%S')
        assert int(first_row[3]) == first_build['duration']
        if len(first_row[4]) == 0:
            assert first_build['description'] == None
        else:
            assert first_row[4] == first_build['description']


if __name__ == '__main__':
    unittest.main()
