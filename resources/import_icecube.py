"""
Import publications from IceCube website.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

import motor.motor_asyncio
import requests
from rest_tools.server import from_environment


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pubs.utils import add_pub


url = 'https://icecube.wisc.edu/pubs/special'

default_config = {
    'DB_URL': 'mongodb://localhost/pub_db',
}
config = from_environment(default_config)


async def main():
    logging.info(f'DB: {config["DB_URL"]}')
    db_url, db_name = config['DB_URL'].rsplit('/', 1)
    logging.info(f'DB name: {db_name}')
    db = motor.motor_asyncio.AsyncIOMotorClient(db_url)[db_name]

    r = requests.get(url)
    r.raise_for_status()
    data = r.text

    for line in data.split('\n'):
        line = line.strip()
        if not line:
            continue
        _, title, authors, type, citation, download, year, month = line.split('\t')
        title = title.strip(' "\'')
        ret = await db.publications.find_one({'title': title})
        if ret:
            logging.info(f'skipping {title}')
            continue
        logging.info(f'processing {title}')

        authors = [authors.strip(' "\'')]
        type = type.strip(' "\'')
        if type == 'theses':
            type = 'thesis'
        elif type == 'conf':
            type = 'proceeding'
        citation = citation.strip(' "\'')
        download = download.strip(' "\'').split('|')
        try:
            c, d = citation.rsplit(',', 1)
            d = d.strip()
            if '-' in d:
                d = d.split('-')[0]+' '+d.split(' ',1)[-1]
            date = datetime.strptime(d.strip(), "%d %B %Y").isoformat()
            citation = c.strip()
        except ValueError:
            if month == 'NULL':
                month = '1'
            date = datetime(year=int(year), month=int(month), day=1).isoformat()
        except Exception:
            raise

        doc = {
            'title': title,
            'authors': authors,
            'pub_type': type,
            'citation': citation,
            'date': date,
            'downloads': download,
            'projects': ['icecube'],
        }

        try:
            await add_pub(db, **doc)
        except AssertionError:
            logging.info(f'{doc}')
            raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())