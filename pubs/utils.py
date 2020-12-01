from datetime import datetime
import logging

import pymongo
from bson.objectid import ObjectId

from . import PUBLICATION_TYPES, PROJECTS, SITES

def nowstr():
    return datetime.utcnow().isoformat()

def date_format(datestring):
    if 'T' in datestring:
        if '.' in datestring:
            date = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S.%f")
        else:
            date = datetime.strptime(datestring, "%Y-%m-%dT%H:%M:%S")
    else:
        date = datetime.strptime(datestring, "%Y-%m-%d")
    return date.strftime("%d %B %Y")

def create_indexes(db_url, db_name, background=True):
    db = pymongo.MongoClient(db_url)[db_name]
    indexes = db.publications.index_information()
    if 'projects_index' not in indexes:
        logging.info('creating projects_index')
        db.publications.create_index('projects', name='projects_index', background=background)
    if 'date_index' not in indexes:
        logging.info('creating date_index')
        db.publications.create_index('date', name='date_index', background=background)
    if 'text_index' not in indexes:
        logging.info('creating text_index')
        db.publications.create_index([('title', pymongo.TEXT), ('authors', pymongo.TEXT), ('citation', pymongo.TEXT)],
                                     weights={'title': 10, 'authors': 5, 'citation': 1},
                                     name='text_index', background=background)

async def add_pub(db, title, authors, pub_type, citation, date, downloads, projects, sites=None):
    assert isinstance(title, str)
    assert isinstance(authors, list)
    for a in authors:
        assert isinstance(a, str)
    assert pub_type in PUBLICATION_TYPES
    assert isinstance(citation, str)
    assert isinstance(date, str)
    date_format(date)
    assert isinstance(downloads, list)
    for d in downloads:
        assert isinstance(d, str)
    assert isinstance(projects, list)
    for p in projects:
        assert p in PROJECTS
    if not sites:
        sites = []
    for s in sites:
        assert s in SITES
    data = {
        "title": title,
        "authors": authors,
        "type": pub_type,
        "citation": citation,
        "date": date,
        "downloads": downloads,
        "projects": projects,
        "sites": sites,
    }
    await db.publications.insert_one(data)

async def edit_pub(db, mongo_id, title=None, authors=None, pub_type=None, citation=None, date=None, downloads=None, projects=None, sites=None):
    match = {'_id': ObjectId(mongo_id)}
    update = {}
    if title:
        assert isinstance(title, str)
        update['title'] = title
    if authors:
        assert isinstance(authors, list)
        for a in authors:
            assert isinstance(a, str)
        update['authors'] = authors
    if pub_type:
        assert pub_type in PUBLICATION_TYPES
        update['type'] = pub_type
    if citation:
        assert isinstance(citation, str)
        update['citation'] = citation
    if date:
        assert isinstance(date, str)
        date_format(date)
        update['date'] = date
    if downloads:
        assert isinstance(downloads, list)
        for d in downloads:
            assert isinstance(d, str)
        update['downloads'] = downloads
    if projects:
        assert isinstance(projects, list)
        for p in projects:
            assert p in PROJECTS
        update['projects'] = projects
    if sites:
        assert isinstance(sites, list)
        for s in sites:
            assert s in SITES
        update['sites'] = sites

    await db.publications.update_one(match, {'$set': update})
