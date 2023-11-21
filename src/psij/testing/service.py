import argparse
import os
import smtplib
import tempfile
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import bcrypt
import datetime
import json
import secrets
import sys
from pathlib import Path
from typing import Optional, Dict, cast, Tuple, Any, List

import cherrypy
import requests
from bson import ObjectId
from mongoengine import Document, StringField, DateTimeField, connect, DictField, \
    IntField, NotUniqueError

CODE_DB_VERSION = 4
EMAIL_BLOCKLIST_URL = 'https://raw.githubusercontent.com/disposable-email-domains/' \
                      'disposable-email-domains/master/disposable_email_blocklist.conf'


def upgrade_0_to_1() -> None:
    pass


def upgrade_1_to_2() -> None:
    RunEnv.objects().update(skipped_count=0)
    Site.create_index(['last_seen'])
    RunEnv.create_index(['site_id', 'run_id'])
    RunEnv.create_index(['site_id', 'run_id', 'branch'])
    Test.create_index(['site_id', 'run_id', 'branch'])


def upgrade_2_to_3() -> None:
    # Mongoengine automatically creates indexes on unique fields?
    # Auth.create_index(['key_id'])
    # AuthExceptionRequests.create_index(['req_id'])
    # AuthDisabledDomains.create_index(['domain'])
    AuthAllowedEmails.create_index(['email'])


def _add_disabled_domain(domain: str) -> None:
    AuthDisabledDomains(domain=domain).save()


def upgrade_3_to_4() -> None:
    for domain in ['gmail.com', 'yahoo.com']:
        _add_disabled_domain(domain)


DB_UPGRADES = {
    0: upgrade_0_to_1,
    1: upgrade_1_to_2,
    2: upgrade_2_to_3,
    3: upgrade_3_to_4
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


class Auth(Document):
    key_id = StringField(required=True, unique=True)
    hash = StringField(required=True)
    email = StringField(required=True)
    last_used = DateTimeField(required=True)
    # the rounds for bcrypt; just default for now, but if that changes, we need to distinguish
    # between entries that were encoded with one round vs something else
    rounds = IntField(required=True, default=1)


# email domains for which we do not allow registration
class AuthDisabledDomains(Document):
    domain = StringField(required=True, unique=True)


# exceptions to AuthDisabledDomains
class AuthAllowedEmails(Document):
    email = StringField(required=True)
    approved_by = StringField(required=True)
    approved_on = DateTimeField(required=True)
    approved_by_ip = StringField(required=True)


# send admin requests to these emails
class AuthAdminEmails(Document):
    email = StringField(required=True, unique=True)


class AuthExceptionRequests(Document):
    req_id = StringField(required=True, unique=True)
    email = StringField(required=True)
    approver_email = StringField(required=True)


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


class AuthError(Exception):
    def __init__(self, error: str, email: str = '', banned_domain: bool = False, domain: str = '') -> None:
        self.error = error
        self.email = email
        self.banned_domain = banned_domain
        self.domain = domain

    def to_object(self):
        return {'success': False, 'error': self.error, 'email': self.email,
                'bannedDomain': self.banned_domain, 'domain': self.domain}


class TestingAggregatorApp(object):
    def __init__(self, config: Dict[str, Any], secrets: Dict[str, object]) -> None:
        self.seq = 0
        self.config = config
        self.secrets = secrets

    @cherrypy.expose
    def index(self) -> None:
        raise cherrypy.HTTPRedirect('/summary.html')

    @cherrypy.expose
    @cherrypy.tools.json_in()
    def result(self) -> None:
        json = cherrypy.request.json
        if not 'id' in json:
            cherrypy.log('Request does not have an ID. JSON was %s' % json)
            raise cherrypy.HTTPError(400, 'Missing id')
        if not 'key' in json:
            cherrypy.log('No key in request. JSON was %s' % json)
            raise cherrypy.HTTPError(400, 'Missing key. Please go to /auth.html to request a key.')
        site_id = json['id']
        key = json['key']
        data = json['data']

        if ':' in key:
            if not self._check_authorized(site_id, key):
                raise cherrypy.HTTPError(403, 'Invalid key. Please go to /auth.html to request a new key.')
        else:
            if not self._check_authorized_legacy(site_id, key):
                raise cherrypy.HTTPError(403, 'This ID is associated with another key')

        try:
            self.seq += 1
            self._save_test(site_id, data)

            module = data['module']
            function = data['function']
            if module == '_conftest':
                if function == '_discover_environment':
                    self._save_environment(site_id, data)
                if function == '_end':
                    self._end_tests(site_id, data)

            self._update_totals(site_id, data)
        except:
            cherrypy.log('Request json: %s' % json)
            raise

    def _update_totals(self, site_id: str, data: Dict[str, Any]) -> None:
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

    def _save_environment(self, site_id: str, data: Dict[str, object]) -> None:
        env = cast(Dict[str, object], data['extras'])
        config = cast(Dict[str, object], env['config'])
        del env['config']
        maintainer_email = config['maintainer_email']
        site = Site.objects(site_id=site_id).first()
        if site is None:
            site = Site(site_id=site_id, key='', ip=cherrypy.request.remote.ip)
            self._update(site)
        if maintainer_email:
            site.crt_maintainer_email = maintainer_email
            site.save()
        run_env = RunEnv(run_id=data['run_id'], site_id=site_id, config=config, env=env,
                         run_start_time=env['start_time'], branch=env['git_branch'])
        run_env.save()

    def _check_authorized(self, site_id:str, key: str) -> bool:
        key_id, token = self._split_key(key)
        return self._verify_key(key_id, token)

    def _check_authorized_legacy(self, site_id: str, key: str) -> bool:
        entries = Site.objects(site_id=site_id)
        entry = entries.first()
        if entry:
            entry.ip = cherrypy.request.remote.ip
            if key == entry.key:
                self._update(entry)
                return True
            else:
                cherrypy.log('Existing key for %s does not match request key.' % site_id)
                # we do not allow ad-hoc keys any more
                return False
        else:
            cherrypy.log('No key in the DB for site %s' % site_id)
            # nothing yet
            return False

    def _update(self, entry: Site) -> None:
        entry.last_seen = datetime.datetime.utcnow()
        entry.save()

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
            date_limit = datetime.datetime.min

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

            branches: List[Dict[str, Any]] = []
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
                total_failed = 0
                total_completed = 0

                for env in envs:
                    total_failed += env.failed_count
                    total_completed += env.completed_count

                month = date_start.month
                if month not in site_data['months']:
                    month_data: Dict[int, object] = {}
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
        test_runs: List[Dict[str, object]] = []
        resp['test_runs'] = test_runs

        runs = RunEnv.objects(site_id=site_id).order_by('-run_start_time', '+branch')[:100]

        seen: Dict[str, Dict[str, Any]] = {}
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
        resp: Dict[str, object] = {}
        resp['site_id'] = site_id
        resp['run_id'] = run_id
        branches: List[Dict[str, object]] = []
        resp['branches'] = branches

        runs = RunEnv.objects(site_id=site_id, run_id=run_id).order_by('+branch')

        for run in runs:
            test_list: List[Dict[str, object]] = []
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

        resp: Dict[str, Dict[str, object]] = {}

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

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authRequest(self, email: str, ctoken: str) -> object:
        try:
            self._verify_captcha_token(ctoken)
            ix = email.find('@')
            if ix == -1:
                raise AuthError('The email you provided has an incorrect syntax.', email)
            domain = email[ix + 1:]

            if AuthDisabledDomains.objects(domain=domain).count() > 0:
                if AuthAllowedEmails.objects(email=email).count() > 0:
                    self._perform_auth_request(email)
                else:
                    raise AuthError('Invalid domain', email, banned_domain=True, domain=domain)
            else:
                self._perform_auth_request(email)
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error', email=email).to_object()

        return {'success': True}

    def _verify_captcha_token(self, ctoken: str) -> None:
        r = requests.post('https://www.google.com/recaptcha/api/siteverify',
                          data = {'secret': self.secrets['reCAPTCHA-secret-key'],
                                  'response': ctoken})
        if r.status_code != 200:
            cherrypy.log('Recaptcha verification error: %s' % r.json())
            raise AuthError('reCAPTCHA verify error', email='')
        rj = r.json()
        if not rj['success']:
            raise AuthError('reCAPTCHA verify error', email='')

    def _perform_auth_request(self, email: str) -> None:
        salt = bcrypt.gensalt()
        token = secrets.token_hex(24)
        encrypted_token = bcrypt.hashpw(token.encode('ascii'), salt)

        for tries in range(3):
            id = secrets.token_hex(8)
            try:
                Auth.save(Auth(key_id=id, email=email, hash=encrypted_token,
                               last_used=datetime.datetime.utcnow()))
                return self._send_key_email(email, id, token)
            except NotUniqueError:
                pass

        raise AuthError('Failed to generate authentication key', email)

    def _load_email_body(self, file_name: str) -> str:
        if file_name[0] == '/':
            path = file_name
        else:
            dir = os.path.dirname(__file__)
            path = dir + '/' + file_name

        with open(path) as f:
            return f.read()

    def _load_email_bodies(self, file_prefix: str, params: Dict[str, str]) -> MIMEMultipart:
        body_plain = self._load_email_body(file_prefix + '.plain').format(**params)
        body_html = self._load_email_body(file_prefix + '.html').format(**params)
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body_plain, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))
        return msg


    def _send_key_email(self, email: str, id: str, token: str) -> None:

        msg = self._load_email_bodies(self.config['auth-email']['body'], {'id': id, 'token': token})

        source = self.config['auth-email']['from']

        msg['Subject'] = 'Your ' + self.config['project-name'] + ' testing dashboard key'
        msg['From'] = source
        msg['To'] = email

        self._send_email(source, email, msg)

    def _send_email(self, source: str, email: str, msg: MIMEMultipart) -> None:
        smtp = smtplib.SMTP('localhost')
        smtp.sendmail(source, email, msg.as_string())
        smtp.quit()

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authRevoke(self, project: str, key: str, ctoken: str) -> object:
        try:
            self._verify_captcha_token(ctoken)

            id, token = self._split_key(key)
            if not self._verify_key(id, token):
                raise AuthError('Invalid key')
            Auth.objects(key_id=id).delete()
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error').to_object()

        return {'success': True}

    def _verify_key(self, key_id: str, key: str) -> bool:
        auth = Auth.objects(key_id=key_id).first()

        if auth is None:
            raise cherrypy.HTTPError(403, 'Key %s not found. Please go to /auth.html to request a '
                                          'new key.' % key_id)
        encrypted_key = bcrypt.hashpw(key.encode('ascii'), auth.hash.encode('ascii'))
        if encrypted_key.decode('ascii') == auth.hash:
            auth.update(last_used=datetime.datetime.utcnow())
            return True
        else:
            cherrypy.log('Key does not match')
            return False

    def _split_key(self, key: str) -> Tuple[str, str]:
        ix = key.find(':')
        if ix == -1:
            cherrypy.log('Invalid key: %s' % key)
            raise AuthError('Invalid code')

        return key[:ix], key[ix + 1:]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authExceptionRequest(self, email: str, reason: str) -> object:
        try:
            self._send_exception_emails(email, reason)
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error').to_object()

        return {'success': True}

    def _send_exception_emails(self, email: str, reason: str) -> None:
        emails = [o.email for o in AuthAdminEmails.objects()]
        if len(emails) == 0:
            emails = [self.config['auth-email']['fallback-admin-email']]
        for admin in emails:
            id = secrets.token_hex(16)
            AuthExceptionRequests(req_id=id, email=email, approver_email=admin).save()
            self._send_exception_email(admin, email, reason, id)

    def _send_exception_email(self, to: str, email: str, reason: str, id: str) -> None:

        approve_url = self.config['auth-email']['callback-url'] \
                     + '/exception-control.html?action=approve&req_id=' + id
        reject_url = self.config['auth-email']['callback-url'] \
                    + '/exception-control.html?action=reject&req_id=' + id
        project_name = self.config['project-name']

        msg = self._load_email_bodies(self.config['auth-email']['exception-body'],
                                      {'project': project_name, 'email': email, 'reason': reason,
                                       'approveUrl': approve_url, 'rejectUrl': reject_url})

        source = self.config['auth-email']['from']

        msg['Subject'] = project_name + ' email exception request'
        msg['From'] = source
        msg['To'] = to

        self._send_email(source, to, msg)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authExceptionAction(self, req_id: str, action: str) -> object:
        try:
            reqs = AuthExceptionRequests.objects(req_id=req_id)
            if len(reqs) == 0:
                raise AuthError('Exception request not found')
            req = reqs.first()
            if action == 'approve':
                headers = cherrypy.request.headers
                if 'X-Forwarded-For' in headers:
                    ip = headers['X-Forwarded-For']
                else:
                    ip = cherrypy.request.remote.ip
                AuthAllowedEmails(email=req.email, approved_by=req.approver_email,
                                  approved_on=datetime.datetime.utcnow(),
                                  approved_by_ip=ip).save()
            self._send_exception_confirmation_email(req.email, action)
            req.delete()
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error').to_object()

        return {'success': True}

    def _send_exception_confirmation_email(self, to: str, action: str) -> None:
        authpage = self.config['auth-email']['callback-url'] + '/auth.html'
        project_name = self.config['project-name']
        if action == 'approve':
            msg = self._load_email_bodies(self.config['auth-email']['exception-approved'],
                                          {'email': to, 'authpage': authpage})
            msg['Subject'] = project_name + ' email exception approved'
        else:
            msg = self._load_email_bodies(self.config['auth-email']['exception-rejected'],
                                          {'email': to, 'authpage': authpage})
            msg['Subject'] = project_name + ' email exception rejected'

        source = self.config['auth-email']['from']

        msg['From'] = source
        msg['To'] = to

        self._send_email(source, to, msg)

class Server:
    def __init__(self, port: int = 9909, config_path: str = 'config.json',
                 secrets_path: str = 'secrets.json') -> None:
        self.port = port
        self.config = self._read_file(config_path)
        self.secrets = self._read_file(secrets_path)

    def _read_file(self, path: str) -> Dict[str, object]:
        if path[0] == '/':
            abs_path = path
        else:
            abs_path = os.path.dirname(__file__) + '/' + path
        with open(abs_path, 'r') as f:
            return json.load(f)

    def start(self) -> None:
        cherrypy.log('webpath: %s' % (Path().absolute() / 'web'))

        json_encoder = CustomJSONEncoder()

        def json_handler(*args, **kwargs):
            value = cherrypy.serving.request._json_inner_handler(*args, **kwargs)
            return json_encoder.iterencode(value)

        cherrypy.config.update({
            'server.socket_port': self.port,
            'server.socket_host': '0.0.0.0',
            'tools.proxy.on': True,
            'tools.proxy.local': 'Host'
        })
        cherrypy.quickstart(TestingAggregatorApp(self.config, self.secrets), '/', {
            '/': {
                'tools.staticdir.root': str(Path(__file__).parent.parent.absolute() / 'web'),
                'tools.staticdir.on': True,
                'tools.staticdir.dir': '',
                'tools.json_out.handler': json_handler
            }
        })


def upgrade_db(v: Version) -> Version:
    if v.version in DB_UPGRADES:
        cherrypy.log('Upgrading DB from %s to %s' % (v.version, v.version + 1))
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


def update_email_blocklist():
    cherrypy.log('updating blocklist')
    r = requests.get(EMAIL_BLOCKLIST_URL)
    r.raise_for_status()
    for line in r.content.splitlines():
        try:
            AuthDisabledDomains(domain=line).save()
        except NotUniqueError:
            pass


def main() -> None:
    check_db()
    update_email_blocklist()
    parser = argparse.ArgumentParser(description='Starts test aggregation server')
    parser.add_argument('-p', '--port', action='store', type=int, default=9909,
                        help='The port on which to start the server.')
    parser.add_argument('-c', '--config', action='store', type=str, default='config.json',
                        help='A configuration file. A relative path points to a file inside the '
                             'source package.')
    parser.add_argument('-s', '--secrets', action='store', type=str, default='secrets.json',
                        help='A file containing authentication keys/tokens.')
    args = parser.parse_args(sys.argv[1:])
    server = Server(args.port, args.config, args.secrets)
    server.start()


if __name__ == '__main__':
    main()
