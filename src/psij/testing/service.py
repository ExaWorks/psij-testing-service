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
from typing import Optional, Dict, cast, Tuple

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


AUTH_EMAIL_DATA = {
    'PSI/J': {
        'from': 'noreply@testing.psij.io',
        'callback-url': 'https://testing.psij.io',
        'body': 'psij-auth',
    },
    'SDK': {
        'from': 'noreply@testing.sdk.exaworks.org',
        'callback-url': 'https://testing.sdk.exaworks.org',
        'body': 'sdk-auth'
    }
}

EXCEPTION_EMAIL_BODY = 'exception'
EXCEPTION_APPROVED_BODY = 'exception-approved'
EXCEPTION_REJECTED_BODY = 'exception-rejected'



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
            raise cherrypy.HTTPError(400, 'Missing key. Please go to /auth.html to request a key.')
        site_id = json['id']
        key = json['key']
        data = json['data']

        if ':' in key:
            site = self._check_authorized(site_id, key)
            if not site:
                raise cherrypy.HTTPError(403, 'Invalid key. Please go to /auth.html to request a new key.')
        else:
            site = self._check_authorized_legacy(site_id, key)
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
            cherrypy.log('Request json: %s' % json)
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

    def _check_authorized(self, id:str, key: str) -> Optional[Site]:
        id, token = self._split_key(key)
        if not self._verify_key(id, token):
            return None
        return Site.objects(site_id=id).first()

    def _check_authorized_legacy(self, id: str, key: str) -> Optional[Site]:
        entries = Site.objects(site_id=id)
        entry = entries.first()
        if entry:
            entry.ip = cherrypy.request.remote.ip
            if key == entry.key:
                return self._update(entry)
            else:
                # we do not allow ad-hoc keys any more
                return None
        else:
            # nothing yet
            return None

    def _update(self, entry: Site) -> Site:
        entry.last_seen = datetime.datetime.utcnow()
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

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authRequest(self, project: str, email: str, ctoken: str) -> object:
        try:
            self._verify_captcha_token(ctoken)
            ix = email.find('@')
            if ix == -1:
                raise AuthError('The email you provided has an incorrect syntax.', email)
            domain = email[ix + 1:]

            if AuthDisabledDomains.objects(domain=domain).count() > 0:
                if AuthAllowedEmails.objects(email=email).count() > 0:
                    self._perform_auth_request(project, email)
                else:
                    raise AuthError('Invalid domain', email, banned_domain=True, domain=domain)
            else:
                self._perform_auth_request(project, email)
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error', email=email).to_object()

        return {'success': True}

    def _verify_captcha_token(self, ctoken: str) -> None:
        r = requests.post('https://www.google.com/recaptcha/api/siteverify',
                          data = {'secret': os.getenv('RECAPTCHA_SECRET_KEY'), 'response': ctoken})
        if r.status_code != 200:
            print(r.json())
            raise AuthError('reCAPTHCA verify error', email='')
        rj = r.json()
        if not rj['success']:
            raise AuthError('reCAPTHCA verify error', email='')

    def _perform_auth_request(self, project: str, email: str) -> None:
        salt = bcrypt.gensalt()
        token = secrets.token_hex(24)
        encrypted_token = bcrypt.hashpw(token.encode('ascii'), salt)

        for tries in range(3):
            id = secrets.token_hex(8)
            try:
                Auth.save(Auth(key_id=id, email=email, hash=encrypted_token,
                               last_used=datetime.datetime.utcnow()))
                return self._send_key_email(project, email, id, token)
            except NotUniqueError:
                pass

        raise AuthError('Failed to generate authentication key', email)

    def _load_email_body(self, file_name: str) -> str:
        dir = os.path.dirname(__file__)
        with open(dir + '/mailtemplates/' + file_name) as f:
            return f.read()

    def _load_email_bodies(self, file_prefix: str, params: Dict[str, str]) -> MIMEMultipart:
        body_plain = self._load_email_body(file_prefix + '.plain').format(**params)
        body_html = self._load_email_body(file_prefix + '.html').format(**params)
        msg = MIMEMultipart('alternative')
        msg.attach(MIMEText(body_plain, 'plain'))
        msg.attach(MIMEText(body_html, 'html'))
        return msg


    def _send_key_email(self, project: str, email: str, id: str, token: str) -> None:
        if project not in AUTH_EMAIL_DATA:
            raise AuthError('Unknown project: ' + project, email)

        msg = self._load_email_bodies(AUTH_EMAIL_DATA[project]['body'], {'id': id, 'key': token})

        source = AUTH_EMAIL_DATA[project]['from']

        msg['Subject'] = 'Your ' + project + ' testing dashboard key'
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

    def _verify_key(self, id: str, key: str) -> None:
        auth = Auth.objects(key_id=id).first()

        encrypted_key = bcrypt.hashpw(key.encode('ascii'), auth.hash.encode('ascii'))
        if encrypted_key.decode('ascii') == auth.hash:
            auth.update(last_used=datetime.datetime.utcnow())
            return True
        else:
            return False

    def _split_key(self, key: str) -> Tuple[str, str]:
        ix = key.find(':')
        if ix == -1:
            raise AuthError('Invalid code')

        return key[:ix], key[ix + 1:]

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authExceptionRequest(self, project: str, email: str, reason: str) -> object:
        try:
            self._send_exception_emails(project, email, reason)
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error').to_object()

        return {'success': True}

    def _send_exception_emails(self, project: str, email: str, reason: str) -> None:
        for o in AuthAdminEmails.objects():
            id = secrets.token_hex(16)
            AuthExceptionRequests(req_id=id, email=email, approver_email=o.email).save()
            self._send_exception_email(o.email, project, email, reason, id)

    def _send_exception_email(self, to: str, project: str, email: str, reason: str,
                              id: str) -> None:
        if project not in AUTH_EMAIL_DATA:
            raise AuthError('Unknown project: ' + project, email)

        approveUrl = AUTH_EMAIL_DATA[project]['callback-url'] \
                     + '/exception-control.html?action=approve&req_id=' + id
        rejectUrl = AUTH_EMAIL_DATA[project]['callback-url'] \
                    + '/exception-control.html?action=reject&req_id=' + id

        msg = self._load_email_bodies(EXCEPTION_EMAIL_BODY, {'project': project, 'email': email,
                                                             'reason': reason,
                                                             'approveUrl': approveUrl,
                                                             'rejectUrl': rejectUrl})

        source = AUTH_EMAIL_DATA[project]['from']

        msg['Subject'] = project + ' email exception request'
        msg['From'] = source
        msg['To'] = to

        self._send_email(source, to, msg)

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def authExceptionAction(self, project: str, req_id: str, action: str) -> object:
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
            self._send_exception_confirmation_email(project, req.email, action)
            req.delete()
        except AuthError as err:
            return err.to_object()
        except Exception:
            traceback.print_exc()
            return AuthError('Internal error').to_object()

        return {'success': True}

    def _send_exception_confirmation_email(self, project: str, to: str, action: str) -> None:
        if project not in AUTH_EMAIL_DATA:
            raise AuthError('Unknown project: ' + project)

        authpage = AUTH_EMAIL_DATA[project]['callback-url'] + '/auth.html'
        if action == 'approve':
            msg = self._load_email_bodies(EXCEPTION_APPROVED_BODY, {'email': to,
                                                                   'authpage': authpage})
            msg['Subject'] = project + ' email exception approved'
        else:
            msg = self._load_email_bodies(EXCEPTION_REJECTED_BODY, {'email': to,
                                                                  'authpage': authpage})
            msg['Subject'] = project + ' email exception rejected'

        source = AUTH_EMAIL_DATA[project]['from']

        msg['From'] = source
        msg['To'] = to

        self._send_email(source, to, msg)

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
    print('updating blocklist')
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
    args = parser.parse_args(sys.argv[1:])
    server = Server(args.port)
    server.start()


if __name__ == '__main__':
    main()
