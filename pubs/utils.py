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
    if 'title_index' not in indexes:
        logging.info('creating title_index')
        db.publications.create_index([('title', pymongo.TEXT)], name='title_index', background=background)
