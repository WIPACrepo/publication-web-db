import asyncio

import pytest
from rest_tools.client import AsyncSession
from bs4 import BeautifulSoup

from pubs.utils import nowstr, add_pub

from .util import port, mongo_client, server


async def get_pubs(*args, **kwargs):
    s = AsyncSession(retries=0, backoff_factor=1)
    r = await asyncio.wrap_future(s.get(*args, **kwargs))
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    return soup.select('.publication')

@pytest.mark.asyncio
async def test_no_pubs(server):
    db, url = server

    pubs = await get_pubs(url)
    assert pubs == []

@pytest.mark.asyncio
async def test_single_pub(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'], abstract="An abstract",
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    pubs = await get_pubs(url)
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title'
    assert pubs[0].select('.author')[0].string == 'auth'
    assert pubs[0].select('.abstract')[0].string == 'An abstract'
    assert pubs[0].select('.project')[0].string == 'IceCube'

@pytest.mark.asyncio
async def test_multiple_pubs(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    pubs = await get_pubs(url)
    assert len(pubs) == 3
    # order by reversed date
    assert pubs[0].select('.title')[0].string == 'Test Title3'
    assert pubs[1].select('.title')[0].string == 'Test Title2'
    assert pubs[2].select('.title')[0].string == 'Test Title'

@pytest.mark.asyncio
async def test_project(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['hawc'])

    pubs = await get_pubs(url, params={'projects': 'hawc'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'
    assert pubs[0].select('.project')[0].string == 'HAWC'

@pytest.mark.asyncio
async def test_multi_project(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['hawc'])

    await add_pub(db, title='Test Title3', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube','hawc'])

    pubs = await get_pubs(url, params={'projects': ['hawc', 'icecube']})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title3'
    assert set(x.string for x in pubs[0].select('.project')) == set(['HAWC', 'IceCube'])

@pytest.mark.asyncio
async def test_hide_projects(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['hawc'])

    pubs = await get_pubs(url, params={'projects': 'hawc', 'hide_projects': True})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'
    assert pubs[0].select('.project') == []

    pubs = await get_pubs(url, params={'projects': 'hawc', 'hide_projects': 'false'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'
    assert pubs[0].select('.project') != []

@pytest.mark.asyncio
async def test_dates(server):
    db, url = server

    await add_pub(db, title='Test Title1', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date='2020-01-02',
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date='2020-02-03',
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date='2020-03-04',
                  downloads=[], projects=['icecube'])

    pubs = await get_pubs(url, params={'start_date': '2020-02-02'})
    assert len(pubs) == 2
    # order by reversed date
    assert pubs[0].select('.title')[0].string == 'Test Title3'
    assert pubs[1].select('.title')[0].string == 'Test Title2'

    pubs = await get_pubs(url, params={'end_date': '2020-02-02'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title1'

    pubs = await get_pubs(url, params={'start_date': '2020-02-01', 'end_date': '2020-03-01'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'

    pubs = await get_pubs(url, params={'start_date': '2020-04-01'})
    assert len(pubs) == 0

    pubs = await get_pubs(url, params={'end_date': '2019-04-01'})
    assert len(pubs) == 0

@pytest.mark.asyncio
async def test_types(server):
    db, url = server

    await add_pub(db, title='Test Title1', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="proceeding", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth'], abstract='',
                  pub_type="thesis", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    pubs = await get_pubs(url, params={'type': 'journal'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title1'

    pubs = await get_pubs(url, params={'type': 'proceeding'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'

    pubs = await get_pubs(url, params={'type': 'thesis'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title3'

    pubs = await get_pubs(url, params={'type': ['journal','thesis']})
    assert len(pubs) == 2
    assert pubs[0].select('.title')[0].string == 'Test Title3'
    assert pubs[1].select('.title')[0].string == 'Test Title1'

@pytest.mark.asyncio
async def test_title(server):
    db, url = server

    await add_pub(db, title='Test Title1', authors=['auth'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'], abstract='',
                  pub_type="proceeding", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth'], abstract='',
                  pub_type="thesis", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    pubs = await get_pubs(url, params={'search': 'title1'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title1'

@pytest.mark.asyncio
async def test_authors(server):
    db, url = server

    await add_pub(db, title='Test Title1', authors=['auth1'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth2'], abstract='',
                  pub_type="proceeding", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth1', 'auth3'], abstract='',
                  pub_type="thesis", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    pubs = await get_pubs(url, params={'authors': 'auth1'})
    assert len(pubs) == 2
    assert pubs[0].select('.title')[0].string == 'Test Title3'
    assert pubs[1].select('.title')[0].string == 'Test Title1'

    pubs = await get_pubs(url, params={'authors': 'auth2'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'

    pubs = await get_pubs(url, params={'authors': 'auth3'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title3'

    pubs = await get_pubs(url, params={'authors': 'auth4'})
    assert len(pubs) == 0


@pytest.mark.asyncio
async def test_csv(server):
    db, url = server

    await add_pub(db, title='Test Title1', authors=['auth1'], abstract='',
                  pub_type="journal", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth2'], abstract='',
                  pub_type="proceeding", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth1', 'auth3'], abstract='',
                  pub_type="thesis", citation="TestJournal", date=nowstr(),
                  downloads=[], projects=['icecube'])

    await add_pub(db, title='Test Title4', authors=['auth1', 'auth4'], abstract='the abstract',
                  pub_type="internal", citation="TestReport", date=nowstr(),
                  downloads=[], projects=['icecube'])

    s = AsyncSession(retries=0, backoff_factor=1)
    r = await asyncio.wrap_future(s.get(url+'/csv'))
    r.raise_for_status()
    