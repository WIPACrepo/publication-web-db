"""
Server for publication db
"""

import os
import logging
import binascii
from functools import wraps
from urllib.parse import urlparse
from datetime import datetime
import base64

from tornado.web import RequestHandler, HTTPError
from rest_tools.server import RestServer, from_environment
# from rest_tools.server import catch_error, authenticated

import motor.motor_asyncio

from . import __version__ as version
from . import PUBLICATION_TYPES, PROJECTS
from .utils import create_indexes

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

def date_format(datestring):
    if 'T' in datestring:
        if '.' in datestring:
            date = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            date = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S")
    else:
        date = datetime.strptime(datestring, "%Y-%m-%d")
    return date.strftime("%d %B %Y")

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

    async def get_pubs(self):
        match = {}

        if projects := self.get_arguments('projects'):
            match['projects'] = {"$in": projects}

        start = self.get_argument('start_date', None)
        end = self.get_argument('end_date', None)
        if start and end:
            match['date'] = {"$gte": start, "$lte": end}
        elif start:
            match['date'] = {"$gte": start}
        elif end:
            match['date'] = {"$lte": end}

        if types := self.get_arguments('type'):
            match['type'] = {"$in": types}

        if search := self.get_argument('search', None):
            match['$text'] = {"$search": search}

        if authors := self.get_arguments('authors'):
            match['authors'] = {"$in": authors}
        
        pubs = []
        async for row in self.db.publications.find(match, projection={'_id': False}):
            pubs.append(row)
        pubs.sort(key=lambda pub: pub['date'], reverse=True)

        return {
            "publications": pubs,
            "projects": projects,
            "start_date": start,
            "end_date": end,
            "type": types,
            "search": search,
            "authors": authors,
        }

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
            authors = row["authors"]
        return authors

class Main(BaseHandler):
    async def get(self):
        hide_projects = self.get_argument('hide_projects', 'false').lower() == 'true'

        pubs = await self.get_pubs()

        self.render('main.html', **pubs, hide_projects=hide_projects)

class Manage(BaseHandler):
    @basic_auth
    async def get(self):
        pubs = await self.get_pubs()
        self.render('manage.html', **pubs)

    @basic_auth
    async def post(self):
        pubs = await self.get_pubs()
        self.render('manage.html', **pubs)

class New(BaseHandler):
    @basic_auth
    async def get(self):
        existing_authors = await self.get_authors()
        self.render('new.html', existing_authors=existing_authors)

    @basic_auth
    async def post(self):
        try:
            doc = {
                'title': self.get_argument('title').strip(),
                'authors': self.get_arguments('existing_authors')+[a.strip() for a in self.get_argument('new_authors').split('\n') if a.strip()],
                'date': self.get_argument('date'),
                'type': self.get_argument('type'),
                'citation': self.get_argument('citation').strip(),
                'downloads': [d.strip() for d in self.get_argument('downloads').split('\n') if d.strip()],
                'projects': self.get_arguments('projects'),
            }
            await self.db.publications.insert_one(doc)

            self.redirect('/')
        except Exception as e:
            self.render('new.html', error=e)

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
    server.add_route(r'/manage', Manage, main_args)
    server.add_route(r'/new', New, main_args)

    server.startup(address=config['HOST'], port=config['PORT'])

    return server
