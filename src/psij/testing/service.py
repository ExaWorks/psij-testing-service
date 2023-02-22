import argparse
import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, cast

import cherrypy
from bson import ObjectId
from mongoengine import Document, StringField, DateTimeField, connect, DictField, BooleanField, \
    IntField


logger = logging.getLogger(__name__)


CODE_DB_VERSION = 2


def upgrade_0_to_1() -> None:
    pass


def upgrade_1_to_2() -> None:
    RunEnv.objects().update(skipped_count=0)
    Site.create_index(['last_seen'])
    RunEnv.create_index(['site_id', 'run_id'])
    RunEnv.create_index(['site_id', 'run_id', 'branch'])
    Test.create_index(['site_id', 'run_id', 'branch'])


DB_UPGRADES = {
    0: upgrade_0_to_1,
    1: upgrade_1_to_2
}

class Version(Document):
    version = IntField(required=True)


class Site(Document):
    site_id = StringField(required=True, unique=True)
    key = StringField(required=True)
    last_seen = DateTimeField(required=True)
    crt_maintainer_email = StringField()
    ip = StringField()


class Test(Document):
    site_id = StringField(required=True)
    test_start_time = DateTimeField(required=True)
    test_end_time = DateTimeField(required=True)
    stdout = StringField()
    stderr = StringField()
    log = StringField()
    module = StringField()
    cls = StringField()
    function = StringField()
    test_name = StringField()
    results = DictField()
    run_id = StringField(required=True)
    branch = StringField(required=True)
    extras = DictField()


class RunEnv(Document):
    run_id = StringField(required=True)
    site_id = StringField(required=True)
    env = DictField()
    config = DictField()
    run_start_time = DateTimeField(required=True)
    branch = StringField(required=True)
    run_end_time = DateTimeField()
    failed_count = IntField(default=0)
    completed_count = IntField(default=0)
    skipped_count = IntField(default=0)


def strtime(d):
    return d.strftime('%a, %b %d, %Y - %H:%M')


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return obj.strftime('%a, %b %d, %Y - %H:%M:%S')
        if isinstance(obj, datetime.date):
            return '{"date": true, "year": %s, "month": %s, "day": %s}' % (obj.year, obj.month,
                                                                           obj.day)
        if isinstance(obj, ObjectId):
            return str(obj)
        return super().default(obj)

    def iterencode(self, value):
        for chunk in super().iterencode(value):
            yield chunk.encode("utf-8")


def add_cors_headers():
    headers = cherrypy.response.headers
    headers['Access-Control-Allow-Origin'] = '*'
    headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept'


class TestingAggregatorApp(object):
    def __init__(self):
        self.seq = 0

    @cherrypy.expose
    def index(self) -> None:
        raise cherrypy.HTTPRedirect('/summary.html')

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def result(self) -> None:
        json = cherrypy.request.json
        if not 'id' in json:
            raise cherrypy.HTTPError(400, 'Missing id')
        if not 'key' in json:
            raise cherrypy.HTTPError(400, 'Missing key')
        site_id = json['id']
        key = json['key']
        data = json['data']

        site = self._check_authorized(site_id, key)
        if not site:
            raise cherrypy.HTTPError(403, 'This ID is associated with another key')

        try:
            self.seq += 1
            self._save_test(site_id, data)

            module = data['module']
            function = data['function']
            if module == '_conftest':
                if function == '_discover_environment':
                    self._save_environment(site, data)
                if function == '_end':
                    self._end_tests(site_id, data)

            self._update_totals(site_id, data)
        except:
            logger.info('Request json: %s' % json)
            raise

    def _update_totals(self, site_id, data: Dict[str, object]) -> None:
        run_id = data['run_id']
        branch = data['branch']

        results = data['results']
        failed = False
        skipped = False
        for k, v in results.items():
            if v['status'] == 'failed':
                failed = True
            if k == 'call' and v['status'] == 'skipped':
                skipped = True
        if failed:
            RunEnv.objects(site_id=site_id, run_id=run_id, branch=branch).update(inc__failed_count=1)
        elif skipped:
            RunEnv.objects(site_id=site_id, run_id=run_id, branch=branch).update(inc__skipped_count=1)
        else:
            RunEnv.objects(site_id=site_id, run_id=run_id, branch=branch).update(inc__completed_count=1)

    def _end_tests(self, site_id: str, data: Dict[str, object]) -> None:
        run_id = data['run_id']
        branch = data['branch']
        time = data['test_end_time']
        RunEnv.objects(site_id=site_id, run_id=run_id, branch=branch).update(run_end_time=time)

    def _save_test(self, site_id: str, data: Dict[str, object]) -> None:
        data['site_id'] = site_id
        Test(**data).save()

    def _save_environment(self, site: Site, data: Dict[str, object]) -> None:
        env = cast(Dict[str, object], data['extras'])
        config = cast(Dict[str, object], env['config'])
        del env['config']
        maintainer_email = config['maintainer_email']
        if maintainer_email:
            site.crt_maintainer_email = maintainer_email
            site.save()
        run_env = RunEnv(run_id=data['run_id'], site_id=site.site_id, config=config, env=env,
                         run_start_time=env['start_time'], branch=env['git_branch'])
        run_env.save()

    def _check_authorized(self, id: str, key: str) -> Optional[Site]:
        entries = Site.objects(site_id=id)
        entry = entries.first()
        if entry:
            entry.ip = cherrypy.request.remote.ip
            if key == entry.key:
                return self._update(entry)
            else:
                now = datetime.datetime.utcnow()
                diff = now - entry.last_seen
                if diff >= datetime.timedelta(days=7):
                    entry.key = key  # update with the new key
                    return self._update(entry)
                else:
                    return None
        else:
            # nothing yet
            return self._update(Site(site_id=id, key=key, ip=cherrypy.request.remote.ip))

    def _update(self, entry: Site) -> Site:
        entry.last_seen = datetime.datetime.utcnow()
        print(entry.site_id)
        entry.save()
        return entry

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def summary(self, inactiveTimeout: str = "10") -> object:
        # get latest batch of tests on each site and return totals for passed/failed

        now = datetime.datetime.now(datetime.timezone.utc)

        try:
            iInactiveTimeout = int(inactiveTimeout)
            date_limit = now - datetime.timedelta(days=iInactiveTimeout)
        except ValueError:
            iInactiveTimeout = 0
        if iInactiveTimeout <= 0:
            date_limit = datetime.date.min

        time_limit = datetime.datetime.combine(date_limit, datetime.datetime.min.time())
        resp = []
        for site in Site.objects(last_seen__gte=time_limit).order_by('site_id'):
            # find last run for site
            try:
                env = RunEnv.objects(site_id=site.site_id).order_by('-run_start_time')[0]
            except IndexError:
                continue
            if env.run_start_time < time_limit:
                continue
            run_id = env.run_id
            # now find all envs/branches with this run id
            envs = RunEnv.objects(site_id=site.site_id, run_id=run_id)

            branches = []
            site_data = {
                'site_id': site.site_id,
                'run_id': run_id,
                'branches': branches,
            }
            site_completed_count = 0
            site_failed_count = 0
            resp.append(site_data)
            any_running = False
            for env in envs:
                running = env.run_end_time is None
                any_running = any_running or running
                branch_data = {
                    'name': env.branch,
                    'completed_count': env.completed_count,
                    'failed_count': env.failed_count,
                    'running': running
                }
                branches.append(branch_data)
                site_completed_count += env.completed_count
                site_failed_count += env.failed_count
            site_data['running'] = any_running
            site_data['completed_count'] = site_completed_count
            site_data['failed_count'] = site_failed_count
            site_data['months'] = {}

            date_start = now
            for days in range(8):
                date_end = date_start + datetime.timedelta(days=1)
                t_start = datetime.datetime.combine(date_start, datetime.datetime.min.time())
                t_end = datetime.datetime.combine(date_end, datetime.datetime.min.time())
                envs = RunEnv.objects(site_id=site.site_id).filter(run_start_time__gte=t_start,
                                                                   run_start_time__lt=t_end)
                print("%s: %s" % (t_start, len(envs)))
                total_failed = 0
                total_completed = 0

                for env in envs:
                    total_failed += env.failed_count
                    total_completed += env.completed_count

                month = date_start.month
                if month not in site_data['months']:
                    month_data = {}  # type Dict[int, object]
                    site_data['months'][month] = month_data
                else:
                    month_data = site_data['months'][month]

                branches = []
                month_data[date_start.day] = {
                    'completed_count': total_completed,
                    'failed_count': total_failed,
                    'branches': branches
                }


                bs = {}
                for env in envs:
                    if env.branch not in bs:
                        bs[env.branch] = {
                            'completed_count': 0,
                            'failed_count': 0
                        }
                    bs[env.branch]['completed_count'] += env.completed_count
                    bs[env.branch]['failed_count'] += env.failed_count

                for k, v in bs.items():
                    branches.append({
                        'completed_count': v['completed_count'],
                        'failed_count': v['failed_count'],
                        'name': k
                    })



                date_start = date_start + datetime.timedelta(days=-1)

        add_cors_headers()
        return resp

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def site(self, site_id) -> object:
        s = Site.objects(site_id=site_id).first()
        resp = {}
        resp['site_id'] = site_id
        test_runs = []
        resp['test_runs'] = test_runs

        runs = RunEnv.objects(site_id=site_id).order_by('-run_start_time', '+branch')[:100]

        seen = {}
        for run in runs:
            if run.run_id in seen:
                run_set = seen[run.run_id]
                if run_set['start_time'] > run.run_start_time:
                    run_set['start_time'] = run.run_start_time
            else:
                run_set = {'start_time': run.run_start_time, 'run_id': run.run_id,
                           'branches': []}
                seen[run.run_id] = run_set
                test_runs.append(run_set)
            branches = run_set['branches']
            branches.append({
                'name': run.branch,
                'failed_count': run.failed_count,
                'completed_count': run.completed_count
            })

        add_cors_headers()
        return resp

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def run(self, site_id, run_id) -> object:
        s = Site.objects(site_id=site_id).first()
        resp = {}
        resp['site_id'] = site_id
        resp['run_id'] = run_id
        branches = []
        resp['branches'] = branches

        runs = RunEnv.objects(site_id=site_id, run_id=run_id).order_by('+branch')

        for run in runs:
            test_list = []
            branch = run.to_mongo().to_dict()
            branch['tests'] = test_list
            branch['name'] = run.branch
            branches.append(branch)

            tests = Test.objects(site_id=site_id, run_id=run_id,
                                 branch=run.branch).order_by('+test_start_time')

            for test in tests:
                test_dict = test.to_mongo().to_dict()
                del test_dict['_id']
                test_list.append(test_dict)

        add_cors_headers()
        return resp

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def tests(self, sites_to_get, tests_to_match) -> object:
        # should probably use json_in and pass all parameters as json
        import json
        sites_to_get = json.loads(sites_to_get)
        tests_to_match = json.loads(tests_to_match)

        now = datetime.datetime.now(datetime.timezone.utc)
        time_limit = now - datetime.timedelta(hours=24)

        tests = Test.objects(site_id__in=sites_to_get,
                             branch__in=['main', 'master'],
                             test_start_time__gt=time_limit,
                             test_name__in=tests_to_match).order_by('-test_start_time')

        resp = {}

        for test in tests:
            if test.site_id not in resp:
                resp[test.site_id] = {}
            # only store the more recent test
            if test.test_name not in resp[test.site_id]:
                test_dict = test.to_mongo().to_dict()
                resp[test.site_id][test.test_name] = test_dict
                for key in ['_id', "stdout", "stderr", "log"]:
                    if key in test_dict:
                        del test_dict[key]

        add_cors_headers()
        return resp


class Server:
    def __init__(self, port: int = 9909) -> None:
        self.port = port

    def start(self) -> None:
        print('webpath: %s' % (Path().absolute() / 'web'))

        json_encoder = CustomJSONEncoder()

        def json_handler(*args, **kwargs):
            value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
            return json_encoder.iterencode(value)

        cherrypy.config.update({
            'server.socket_port': self.port,
            'server.socket_host': '0.0.0.0'
        })
        cherrypy.quickstart(TestingAggregatorApp(), '/', {
            '/': {
                'tools.staticdir.root': str(Path(__file__).parent.parent.absolute() / 'web'),
                'tools.staticdir.on': True,
                'tools.staticdir.dir': '',
                'tools.json_out.handler': json_handler
            }
        })


def upgrade_db(v: Version) -> Version:
    if v.version in DB_UPGRADES:
        logger.info('Upgrading DB from %s to %s' % (v.version, v.version + 1))
        DB_UPGRADES[v.version]()
        v.update(inc__version=1)
        v.reload()
    return v


def check_db() -> None:
    connect(db='psi-j-testing-aggregator')
    vs = Version.objects()
    if len(vs) == 0:
        v = Version(version=0).save()
        v.reload()
    else:
        v = vs[0]

    while v.version < CODE_DB_VERSION:
        v = upgrade_db(v)


def main() -> None:
    check_db()
    parser = argparse.ArgumentParser(description='Starts test aggregation server')
    parser.add_argument('-p', '--port', action='store', type=int, default=9909,
                        help='The port on which to start the server.')
    args = parser.parse_args(sys.argv[1:])
    server = Server(args.port)
    server.start()


if __name__ == '__main__':
    main()
