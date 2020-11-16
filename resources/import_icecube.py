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

        authors = [authors.strip(' "\'')]
        type = type.strip(' "\'')
        if type == 'theses':
            type = 'thesis'
        elif type == 'conf':
            type = 'proceeding'
        citation = citation.strip(' "\'')
        download = download.strip(' "\'').split('|')
        try:
            date = datetime(year=int(year), month=int(month), day=1).isoformat()
        except ValueError:
            date = datetime.now().isoformat()

        # improved date finding
        for part in reversed(citation.split(',')):
            try:
                part = part.split(';',1)[0].split('-',1)[-1].strip()
                date = datetime.strptime(part, "%d %B %Y").isoformat()
                break
            except Exception:
                continue

        ret = await db.publications.find({'title': title, 'type': type, 'authors': authors}).to_list(1000)
        if ret:
            if (title, type, authors) in [
                    ('High Energy Neutrino Astronomy: The Experimental Road', 'proceeding', ['Christian Spiering']),
                    ('Search for Neutralino Dark Matter with the AMANDA Neutrino Telescope and Prospects for IceCube', 'proceeding', ['A. Rizzo for the IceCube Collaboration']),
                    ('IceCube Science', 'proceeding', ['Francis Halzen']),
                    ('IceCube', 'proceeding', ['Albrecht Karle for the IceCube Collaboration']),
                    ('IceCube and the Discovery of High-Energy Cosmic Neutrinos', 'proceeding', ['Francis Halzen']),
                ] and citation not in [r['citation'] for r in ret]:
                logging.info(f'non-dup already entered: {ret}')
            elif (title, type, authors) in [ # skip list to remove dups
                    ('The IceCube Neutrino Telescope', 'proceeding', ['IceCube Collaboration: J. Ahrens et al']),
                    ('Neutrino Astronomy at the South Pole', 'proceeding', ['IceCube Collaboration: A. Achterberg et al']),
                    ('Searches for Annihilating Dark Matter in the Milky Way Halo with IceCube', 'proceeding', ['Samuel Flis and Morten Medici for the IceCube Collaboration']),
                    ('The IceCube Neutrino Observatory - Contributions to the 36th International Cosmic Ray Conference (ICRC2019)', 'proceeding', ['IceCube Collaboration: M. G. Aartsen et al']),
                ]:
                logging.info(f'skipping {line}')
                logging.info(f'  already entered: {ret}')
                continue
            else:
                logging.info(f'bad entry {line}')
                logging.info(f'  already entered: {ret}')
                continue
        logging.info(f'processing {title}')

        doc = {
            'title': title,
            'authors': authors,
            'pub_type': type,
            'citation': citation,
            'date': date,
            'downloads': download,
            'projects': ['icecube'],
            'sites': ['icecube','wipac'],
        }

        try:
            await add_pub(db, **doc)
        except AssertionError:
            logging.info(f'{doc}')
            raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())