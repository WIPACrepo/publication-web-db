"""
Server for publication db
"""

import os
import logging
import binascii
from functools import wraps
from urllib.parse import urlparse
import base64
import csv
from io import StringIO
import itertools

from tornado.web import RequestHandler, HTTPError
from rest_tools.server import RestServer, from_environment, catch_error
import motor.motor_asyncio
import pymongo
from bson.objectid import ObjectId

from . import __version__ as version
from . import PUBLICATION_TYPES, PROJECTS, SITES
from .utils import create_indexes, date_format, add_pub, edit_pub, try_import_file

logger = logging.getLogger('server')

def basic_auth(method):
    @wraps(method)
    async def wrapper(self, *args, **kwargs):
        if not self.current_user:
            header = self.request.headers.get('Authorization')
            if header is None or not header.lower().startswith('basic '):
                self.set_header('WWW-Authenticate', 'Basic realm=IceCube')
                self.set_status(401)
                self.finish()
                return
            raise HTTPError(403, reason="authentication failed")
        return await method(self, *args, **kwargs)
    return wrapper

def get_domain(link):
    """Get domain name of a url"""
    if (not link.startswith('http')) and not link.startswith('//'):
        link = f'//{link}'
    return urlparse(link).netloc

class BaseHandler(RequestHandler):
    def initialize(self, db=None, basic_auth=None, debug=False, **kwargs):
        super().initialize(**kwargs)
        self.db = db
        self.basic_auth = basic_auth if basic_auth else {}
        self.debug = debug

    def set_default_headers(self):
        self._headers['Server'] = f'Pub DB {version}'

    def get_template_namespace(self):
        namespace = super().get_template_namespace()
        namespace['domain'] = get_domain
        namespace['date_format'] = date_format
        namespace['experiment'] = 'IceCube'
        namespace['title'] = ''
        namespace['PUBLICATION_TYPES'] = PUBLICATION_TYPES
        namespace['PROJECTS'] = PROJECTS
        namespace['SITES'] = SITES
        namespace['error'] = None
        namespace['edit'] = False
        return namespace

    def get_current_user(self):
        try:
            type, data = self.request.headers['Authorization'].split(' ', 1)
            if type.lower() != 'basic':
                raise Exception('bad header type')
            logger.debug(f'auth data: {data}')
            auth_decoded = base64.b64decode(data).decode('ascii')
            username, password = str(auth_decoded).split(':', 1)
            if self.basic_auth.get(username, None) == password:
                return username
        except Exception:
            if self.debug and 'Authorization' in self.request.headers:
                logger.info('Authorization: %r', self.request.headers['Authorization'])
            logger.info('failed auth', exc_info=True)
        return None

    def args_to_match_query(self):
        match = {}

        if projects := self.get_arguments('projects'):
            match['projects'] = {"$all": projects}

        if sites := self.get_arguments('sites'):
            match['sites'] = {"$all": sites}

        start = self.get_argument('start_date', '')
        end = self.get_argument('end_date', '')
        if start and end:
            match['date'] = {"$gte": start, "$lte": end}
        elif start:
            match['date'] = {"$gte": start}
        elif end:
            match['date'] = {"$lte": end}

        if types := self.get_arguments('type'):
            match['type'] = {"$in": types}

        if search := self.get_argument('search', ''):
            match['$text'] = {"$search": search}

        if authors := self.get_arguments('authors'):
            match['authors'] = {"$all": authors}

        return match, {
            'projects': projects,
            'sites': sites,
            'start_date': start,
            'end_date': end,
            'type': types,
            'search': search,
            'authors': authors,
        }

    async def count_pubs(self):
        match, _ = self.args_to_match_query()
        return await self.db.publications.count_documents(match)

    async def get_pubs(self, mongoid=False):
        match, args = self.args_to_match_query()

        kwargs = {}
        if not mongoid:
            kwargs['projection'] = {'_id': False}

        if page := self.get_argument('page', None):
            page = int(page)
        if limit := self.get_argument('limit', None):
            limit = int(limit)

        pubs = []
        i = -1
        async for row in self.db.publications.find(match, **kwargs).sort('date', pymongo.DESCENDING):
            i += 1
            if mongoid:
                row['_id'] = str(row['_id'])
            if page is not None and limit and i < page*limit:
                continue
            if 'projects' in row:
                row['projects'].sort()
            if 'sites' in row:
                row['sites'].sort()
            pubs.append(row)
            if page is not None and limit and len(pubs) >= limit:
                break

        args['publications'] = pubs
        return args

    async def get_authors(self):
        aggregation = [
            {"$unwind": "$authors"},
            {"$group": {
                "_id": 0,
                "authornames": {"$addToSet": "$authors"}
            }}
        ]
        authors = []
        async for row in self.db.publications.aggregate(aggregation):
            authors = row["authornames"]
        return authors

class Main(BaseHandler):
    async def get(self):
        hide_projects = self.get_argument('hide_projects', 'false').lower() == 'true'

        pubs = await self.get_pubs()

        self.render('main.html', **pubs, hide_projects=hide_projects)

class CSV(BaseHandler):
    async def get(self):
        pubs = await self.get_pubs()

        f = StringIO()
        writer = csv.DictWriter(f, fieldnames=list(pubs['publications'][0].keys()))
        writer.writeheader()
        for p in pubs['publications']:
            data = {}
            for k in p:
                if isinstance(p[k], list):
                    data[k] = ','.join(p[k])
                else:
                    data[k] = p[k]
            writer.writerow(data)

        self.write(f.getvalue())
        self.set_header('Content-Type', 'text/csv; charset=utf-8')

class Manage(BaseHandler):
    @catch_error
    @basic_auth
    async def get(self):
        existing_authors = await self.get_authors()
        pubs = await self.get_pubs(mongoid=True)
        self.render('manage.html', message='', existing_authors=existing_authors, **pubs)

    @catch_error
    @basic_auth
    async def post(self):
        message = ''
        try:
            if action := self.get_argument('action', None):
                if action == 'delete':
                    mongoid = ObjectId(self.get_argument('pub_id'))
                    await self.db.publications.delete_one({'_id': mongoid})
                elif action == 'new':
                    doc = {
                        'title': self.get_argument('new_title').strip(),
                        'authors': [a.strip() for a in self.get_argument('new_authors').split('\n') if a.strip()],
                        'date': self.get_argument('new_date'),
                        'pub_type': self.get_argument('new_type'),
                        'citation': self.get_argument('new_citation').strip(),
                        'downloads': [d.strip() for d in self.get_argument('new_downloads').split('\n') if d.strip()],
                        'projects': self.get_arguments('new_projects'),
                        'sites': self.get_arguments('new_sites'),
                    }
                    await add_pub(db=self.db, **doc)
                elif action == 'edit':
                    mongoid = ObjectId(self.get_argument('pub_id'))
                    doc = {
                        'title': self.get_argument('new_title').strip(),
                        'authors': [a.strip() for a in self.get_argument('new_authors').split('\n') if a.strip()],
                        'date': self.get_argument('new_date'),
                        'pub_type': self.get_argument('new_type'),
                        'citation': self.get_argument('new_citation').strip(),
                        'downloads': [d.strip() for d in self.get_argument('new_downloads').split('\n') if d.strip()],
                        'projects': self.get_arguments('new_projects'),
                        'sites': self.get_arguments('new_sites'),
                    }
                    await edit_pub(db=self.db, mongo_id=mongoid, **doc)
                elif action == 'import':
                    if not self.request.files:
                        raise Exception('no files uploaded')
                    for files in itertools.chain(self.request.files.values()):
                        for f in files:
                            await try_import_file(self.db, f.body.decode('utf-8-sig'))
                else:
                    raise Exception('bad action')
        except Exception as e:
            if self.debug:
                logging.debug('manage error', exc_info=True)
            message = f'Error: {e}'
        existing_authors = await self.get_authors()
        pubs = await self.get_pubs(mongoid=True)
        self.render('manage.html', message=message, existing_authors=existing_authors, **pubs)

class APIBaseHandler(BaseHandler):
    def write_error(self, status_code=500, **kwargs):
        """Write out custom error json."""
        data = {
            'code': status_code,
            'error': self._reason,
        }
        self.write(data)
        self.finish()

class APIPubs(APIBaseHandler):
    @catch_error
    async def get(self):
        pubs = await self.get_pubs()
        self.write(pubs)

class APIPubsCount(APIBaseHandler):
    @catch_error
    async def get(self):
        pubs = await self.count_pubs()
        self.write({"count": pubs})

class APIFilterDefaults(APIBaseHandler):
    @catch_error
    async def get(self):
        self.write({
            'projects': [],
            'sites': [],
            'start_date': '',
            'end_date': '',
            'type': [],
            'search': '',
            'authors': [],
            'hide_projects': False,
        })

class APITypes(APIBaseHandler):
    @catch_error
    async def get(self):
        self.write(PUBLICATION_TYPES)

class APIProjects(APIBaseHandler):
    @catch_error
    async def get(self):
        self.write(PROJECTS)

def create_server():
    static_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

    default_config = {
        'HOST': 'localhost',
        'PORT': 8080,
        'DEBUG': False,
        'DB_URL': 'mongodb://localhost/pub_db',
        'COOKIE_SECRET': binascii.hexlify(b'secret').decode('utf-8'),
        'BASIC_AUTH': '',  # user:pass,user:pass
    }
    config = from_environment(default_config)

    logging.info(f'DB: {config["DB_URL"]}')
    db_url, db_name = config['DB_URL'].rsplit('/', 1)
    logging.info(f'DB name: {db_name}')
    db = motor.motor_asyncio.AsyncIOMotorClient(db_url)
    create_indexes(db_url, db_name)

    users = {v.split(':')[0]: v.split(':')[1] for v in config['BASIC_AUTH'].split(',') if v}
    logging.info(f'BASIC_AUTH users: {users.keys()}')

    main_args = {
        'debug': config['DEBUG'],
        'db': db[db_name],
        'basic_auth': users,
    }

    server = RestServer(static_path=static_path, template_path=template_path,
                        cookie_secret=config['COOKIE_SECRET'], xsrf_cookies=True,
                        debug=config['DEBUG'])

    server.add_route(r'/', Main, main_args)
    server.add_route(r'/csv', CSV, main_args)
    server.add_route(r'/manage', Manage, main_args)
    server.add_route(r'/api/publications', APIPubs, main_args)
    server.add_route(r'/api/publications/count', APIPubsCount, main_args)
    server.add_route(r'/api/filter_defaults', APIFilterDefaults, main_args)
    server.add_route(r'/api/types', APITypes, main_args)
    server.add_route(r'/api/projects', APIProjects, main_args)

    server.startup(address=config['HOST'], port=config['PORT'])

    return server
