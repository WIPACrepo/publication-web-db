import asyncio

from rest_tools.server import from_environment
import pytest
from bson.objectid import ObjectId

from pubs import PUBLICATION_TYPES, PROJECTS, SITES
import pubs.utils

from .util import mongo_client

def test_nowstr():
    n = pubs.utils.nowstr()
    assert isinstance(n, str)
    assert 'T' in n
    pubs.utils.date_format(n)

def test_date_format():
    assert '03 November 2020' == pubs.utils.date_format('2020-11-03T00:00:00.000000')
    assert '03 November 2020' == pubs.utils.date_format('2020-11-03T00:00:00')
    assert '03 November 2020' == pubs.utils.date_format('2020-11-03')

@pytest.mark.asyncio
async def test_create_indexes(mongo_client):
    default_config = {
       'DB_URL': None,
    }
    config = from_environment(default_config)
    db_url, db_name = config['DB_URL'].rsplit('/', 1)
    pubs.utils.create_indexes(db_url, db_name, background=False)

    indexes = await mongo_client.publications.index_information()
    assert 'text_index' in indexes

@pytest.mark.parametrize('sites', [['icecube', 'wipac'], None])
@pytest.mark.asyncio
async def test_add_pub(mocker, sites):
    db = mocker.AsyncMock()
    args = {
        'title': 'title',
        'authors': ['auth1', 'auth2'],
        'type': 'journal',
        'citation': 'citation',
        'date': '2020-11-03T00:00:00',
        'downloads': ['down1', 'down2'],
        'projects': ['icecube', 'hawc'],
        'sites': sites if sites else []
    }
    await pubs.utils.add_pub(db, title=args['title'], authors=args['authors'], pub_type=args['type'],
            citation=args['citation'], date=args['date'], downloads=args['downloads'],
            projects=args['projects'], sites=sites)

    db.publications.insert_one.assert_called_once_with(args)

@pytest.mark.parametrize('title', ['title', 123])
@pytest.mark.parametrize('authors', [['auth1', 'auth2'], [12], 'author'])
@pytest.mark.parametrize('pub_type', ['journal', 'foo', 12])
@pytest.mark.parametrize('citation', ['citation', 12])
@pytest.mark.parametrize('date', ['2020-11-03T00:00:00', '2020-1111', 2020])
@pytest.mark.parametrize('downloads', [['down1', 'down2'], [12], 'down'])
@pytest.mark.parametrize('projects', [['icecube','hawc'], [12], 12])
@pytest.mark.parametrize('sites', [[12], 12])
@pytest.mark.asyncio
async def test_add_pub_err(mocker, title, authors, pub_type, citation, date, downloads, projects, sites):
    db = mocker.AsyncMock()

    with pytest.raises(Exception):
        await pubs.utils.add_pub(db, title=title, authors=authors, pub_type=pub_type,
                citation=citation, date=date, downloads=downloads, projects=projects, sites=sites)

@pytest.mark.parametrize('title', ['title', None])
@pytest.mark.parametrize('authors', [['auth1', 'auth2'], None])
@pytest.mark.parametrize('pub_type', ['journal', None])
@pytest.mark.parametrize('citation', ['citation', None])
@pytest.mark.parametrize('date', ['2020-11-03T00:00:00', None])
@pytest.mark.parametrize('downloads', [['down1', 'down2'], None])
@pytest.mark.parametrize('projects', [['icecube','hawc'], None])
@pytest.mark.parametrize('sites', [['icecube', 'wipac'], None])
@pytest.mark.asyncio
async def test_edit_pub(mocker, title, authors, pub_type, citation, date, downloads, projects, sites):
    mongo_id = ObjectId()
    args = {}
    if title:
        args['title'] = title
    if authors:
        args['authors'] = authors
    if pub_type:
        args['type'] = pub_type
    if citation:
        args['citation'] = citation
    if date:
        args['date'] = date
    if downloads:
        args['downloads'] = downloads
    if projects:
        args['projects'] = projects
    if sites:
        args['sites'] = sites

    db = mocker.AsyncMock()
    await pubs.utils.edit_pub(db, str(mongo_id), title=title, authors=authors, pub_type=pub_type,
            citation=citation, date=date, downloads=downloads, projects=projects, sites=sites)

    db.publications.update_one.assert_called_once_with({'_id': mongo_id}, {'$set': args})

@pytest.mark.parametrize('title', [123, None])
@pytest.mark.parametrize('authors', [[12], 'author', None])
@pytest.mark.parametrize('pub_type', ['foo', 12, None])
@pytest.mark.parametrize('citation', [12, None])
@pytest.mark.parametrize('date', ['2020-1111', 2020, None])
@pytest.mark.parametrize('downloads', [[12], 'down', None])
@pytest.mark.parametrize('projects', [[12], 12, None])
@pytest.mark.parametrize('sites', [[12], 12])
@pytest.mark.asyncio
async def test_edit_pub_err(mocker, title, authors, pub_type, citation, date, downloads, projects, sites):
    mongo_id = ObjectId()
    db = mocker.AsyncMock()

    with pytest.raises(Exception):
        await pubs.utils.edit_pub(db, str(mongo_id), title=title, authors=authors, pub_type=pub_type,
                citation=citation, date=date, downloads=downloads, projects=projects, sites=sites)

@pytest.mark.asyncio
async def test_import_file_json(mocker):
    db = mocker.AsyncMock()
    json_data = '''{"publications":[{"title":"foo","authors":["bar"],"type":"journal","citation":"cite",
"date":"2020-11-03T00:00:00","downloads":["baz"],"projects":["icecube"],"sites":["icecube","wipac"]}]}'''
    await pubs.utils.try_import_file(db, json_data)

    json_data = '''[{"title":"foo","authors":["bar"],"type":"journal","citation":"cite",
"date":"2020-11-03T00:00:00","downloads":["baz"],"projects":["icecube"],"sites":["icecube","wipac"]}]'''
    await pubs.utils.try_import_file(db, json_data)

@pytest.mark.asyncio
async def test_import_file_csv(mocker):
    db = mocker.AsyncMock()
    csv_data = '''title,authors,type,citation,date,downloads,projects,sites
foo,bar,journal,cite,2020-11-03T00:00:00,baz,icecube,"icecube,wipac"'''
    await pubs.utils.try_import_file(db, csv_data)

@pytest.mark.asyncio
async def test_import_file_csv_authors(mocker):
    db = mocker.AsyncMock()
    csv_data = '''title,authors,type,citation,date,downloads,projects,sites
foo,"bar, baz, and blah",journal,cite,2020-11-03T00:00:00,baz,icecube,"icecube,wipac"'''
    await pubs.utils.try_import_file(db, csv_data)
