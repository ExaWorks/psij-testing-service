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


        #return [resp[0], resp[0], resp[0]]
        DEBUG_RESP = '[{"site_id": "Hategan\'s laptop", "run_id": "2022080310-8bdc484df8187c8040212002a96e4a1e5cf9f521755a18296989109670f0804d", "branches": [{"name": "main", "completed_count": 1, "failed_count": 0, "running": true}], "running": true, "completed_count": 1, "failed_count": 0, "months": {"8": {"3": {"completed_count": 1, "failed_count": 0, "branches": [{"completed_count": 1, "failed_count": 0, "name": "main"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "28": {"completed_count": 237, "failed_count": 33, "branches": [{"completed_count": 79, "failed_count": 11, "name": "deploy_scripts"}, {"completed_count": 79, "failed_count": 11, "name": "main"}, {"completed_count": 79, "failed_count": 11, "name": "setup_version_info"}]}, "27": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}}}}, {"site_id": "axis1.hidden.uoregon.edu", "run_id": "2022080218-00414fb4d08c0f090e951356391d6b522432fbee1d539dfc6af191924e32c0a7", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 107, "failed_count": 16, "branches": [{"completed_count": 107, "failed_count": 16, "name": "main"}]}, "28": {"completed_count": 107, "failed_count": 16, "branches": [{"completed_count": 107, "failed_count": 16, "name": "main"}]}, "27": {"completed_count": 107, "failed_count": 16, "branches": [{"completed_count": 107, "failed_count": 16, "name": "main"}]}}}}, {"site_id": "cori08.nersc.gov", "run_id": "2022080209-47b1d88914dd1da61417d8c446e7312f8a9a21749bfcbfc050f1e5121596c31a", "branches": [{"name": "add_str_to_job_attributes", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 6, "failed_count": 0, "months": {"8": {"3": {"completed_count": 0, "failed_count": 0, "branches": []}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 87, "failed_count": 14, "branches": [{"completed_count": 87, "failed_count": 14, "name": "main"}]}, "28": {"completed_count": 261, "failed_count": 42, "branches": [{"completed_count": 87, "failed_count": 14, "name": "deploy_scripts"}, {"completed_count": 87, "failed_count": 14, "name": "main"}, {"completed_count": 87, "failed_count": 14, "name": "setup_version_info"}]}, "27": {"completed_count": 87, "failed_count": 14, "branches": [{"completed_count": 87, "failed_count": 14, "name": "main"}]}}}}, {"site_id": "doc.llnl.gov", "run_id": "2022072514-476f115745cf9c28b255db4d01c1b90afce3fd1ab3526a1b579a62064ffead3b", "branches": [{"name": "main", "completed_count": 40, "failed_count": 28, "running": false}], "running": false, "completed_count": 40, "failed_count": 28, "months": {"8": {"3": {"completed_count": 0, "failed_count": 0, "branches": []}, "2": {"completed_count": 0, "failed_count": 0, "branches": []}, "1": {"completed_count": 0, "failed_count": 0, "branches": []}}, "7": {"31": {"completed_count": 0, "failed_count": 0, "branches": []}, "30": {"completed_count": 0, "failed_count": 0, "branches": []}, "29": {"completed_count": 0, "failed_count": 0, "branches": []}, "28": {"completed_count": 0, "failed_count": 0, "branches": []}, "27": {"completed_count": 0, "failed_count": 0, "branches": []}}}}, {"site_id": "illyad.hidden.uoregon.edu", "run_id": "2022080219-9c4f6289e5a90e41a0378b4e3884cffc0620007b6471e302f9bcad695a7934bc", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "28": {"completed_count": 237, "failed_count": 33, "branches": [{"completed_count": 79, "failed_count": 11, "name": "deploy_scripts"}, {"completed_count": 79, "failed_count": 11, "name": "main"}, {"completed_count": 79, "failed_count": 11, "name": "setup_version_info"}]}, "27": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}}}}, {"site_id": "jupiter.hidden.uoregon.edu", "run_id": "2022080307-6ae90668e9210e032d35a7ca6c2d02f6d8cff2143dac2355178164fd86d38f17", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "28": {"completed_count": 237, "failed_count": 33, "branches": [{"completed_count": 79, "failed_count": 11, "name": "deploy_scripts"}, {"completed_count": 79, "failed_count": 11, "name": "main"}, {"completed_count": 79, "failed_count": 11, "name": "setup_version_info"}]}, "27": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}}}}, {"site_id": "mothra.hidden.uoregon.edu", "run_id": "2022080217-6ad22fb3069aca9a415405287953646e2947455e910c9533b2cfc13b38e3c82a", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 59, "failed_count": 9, "branches": [{"completed_count": 59, "failed_count": 9, "name": "main"}]}, "28": {"completed_count": 59, "failed_count": 9, "branches": [{"completed_count": 59, "failed_count": 9, "name": "main"}]}, "27": {"completed_count": 59, "failed_count": 9, "branches": [{"completed_count": 59, "failed_count": 9, "name": "main"}]}}}}, {"site_id": "orthus.nic.uoregon.edu", "run_id": "2022080306-34839c604f5669a85ba23cc2b629d40d68a48220cd1c795282ad4ebf8f9be0cb", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "28": {"completed_count": 237, "failed_count": 33, "branches": [{"completed_count": 79, "failed_count": 11, "name": "deploy_scripts"}, {"completed_count": 79, "failed_count": 11, "name": "main"}, {"completed_count": 79, "failed_count": 11, "name": "setup_version_info"}]}, "27": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}}}}, {"site_id": "reptar.hidden.uoregon.edu", "run_id": "2022080218-df08ff0eadd112d3548def686b7ef0b671dc3579dd39126e3c36de02a56106a3", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "28": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "27": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}}}}, {"site_id": "saturn.hidden.uoregon.edu", "run_id": "2022080301-5830a4c6f6770f8b1835576edb353ebe18783966156e831b5f09e0be7b4aff2e", "branches": [{"name": "main", "completed_count": 2, "failed_count": 0, "running": false}, {"name": "minimal_test_uploads", "completed_count": 2, "failed_count": 0, "running": false}], "running": false, "completed_count": 4, "failed_count": 0, "months": {"8": {"3": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "2": {"completed_count": 6, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "add_str_to_job_attributes"}, {"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "minimal_test_uploads"}]}, "1": {"completed_count": 4, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}, {"completed_count": 2, "failed_count": 0, "name": "test_git_branch_fix"}]}}, "7": {"31": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "30": {"completed_count": 2, "failed_count": 0, "branches": [{"completed_count": 2, "failed_count": 0, "name": "main"}]}, "29": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}, "28": {"completed_count": 237, "failed_count": 33, "branches": [{"completed_count": 79, "failed_count": 11, "name": "deploy_scripts"}, {"completed_count": 79, "failed_count": 11, "name": "main"}, {"completed_count": 79, "failed_count": 11, "name": "setup_version_info"}]}, "27": {"completed_count": 79, "failed_count": 11, "branches": [{"completed_count": 79, "failed_count": 11, "name": "main"}]}}}}]'
        import json
        #return json.loads(DEBUG_RESP)
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
            },
            '/instance': {
                'tools.staticdir.root': '/var/www/html',
                'tools.staticdir.on': True,
                'tools.staticdir.dir': '',
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
