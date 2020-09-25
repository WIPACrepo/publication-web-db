from datetime import datetime
import asyncio

import pytest
from rest_tools.client import AsyncSession
from bs4 import BeautifulSoup

from pubs import PUBLICATION_TYPES

from .util import port, mongo_client, server

def nowstr():
    return datetime.utcnow().isoformat()

async def get_pubs(*args, **kwargs):
    s = AsyncSession(retries=0)
    r = await asyncio.wrap_future(s.get(*args, **kwargs))
    r.raise_for_status()
    soup = BeautifulSoup(r.content, 'html.parser')
    return soup.select('.publication')

async def add_pub(db, title, authors, pub_type, journals, date, links, projects):
    assert pub_type in PUBLICATION_TYPES
    data = {
        "title": title,
        "authors": authors,
        "type": pub_type,
        "journals": journals,
        "date": date,
        "downloads": links,
        "projects": projects,
    }
    await db.publications.insert_one(data)

@pytest.mark.asyncio
async def test_no_pubs(server):
    db, url = server

    pubs = await get_pubs(url)
    assert pubs == []

@pytest.mark.asyncio
async def test_single_pub(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['icecube'])

    pubs = await get_pubs(url)
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title'
    assert pubs[0].select('.author')[0].string == 'auth'
    assert pubs[0].select('.project')[0].string == 'IceCube'

@pytest.mark.asyncio
async def test_multiple_pubs(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['icecube'])

    await add_pub(db, title='Test Title3', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['icecube'])

    pubs = await get_pubs(url)
    assert len(pubs) == 3
    # order by reversed date
    assert pubs[0].select('.title')[0].string == 'Test Title3'
    assert pubs[1].select('.title')[0].string == 'Test Title2'
    assert pubs[2].select('.title')[0].string == 'Test Title'

@pytest.mark.asyncio
async def test_project(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['hawc'])

    pubs = await get_pubs(url, params={'projects': 'hawc'})
    assert len(pubs) == 1
    assert pubs[0].select('.title')[0].string == 'Test Title2'
    assert pubs[0].select('.project')[0].string == 'HAWC'

@pytest.mark.asyncio
async def test_multi_project(server):
    db, url = server

    await add_pub(db, title='Test Title', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['icecube'])

    await add_pub(db, title='Test Title2', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['hawc'])

    await add_pub(db, title='Test Title3', authors=['auth'],
                  pub_type="journal", journals=["TestJournal"], date=nowstr(),
                  links=[], projects=['ara'])

    pubs = await get_pubs(url, params={'projects': ['hawc', 'icecube']})
    assert len(pubs) == 2
    assert pubs[0].select('.title')[0].string == 'Test Title2'
    assert pubs[0].select('.project')[0].string == 'HAWC'
    assert pubs[1].select('.title')[0].string == 'Test Title'
    assert pubs[1].select('.project')[0].string == 'IceCube'
