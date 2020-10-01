from datetime import datetime
import logging

import pymongo


def nowstr():
    return datetime.utcnow().isoformat()

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
