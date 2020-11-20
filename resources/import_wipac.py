"""
Import publications from IceCube website.
"""
import os
import sys
import asyncio
import logging
from datetime import datetime

import motor.motor_asyncio
import pymysql.cursors
from rest_tools.server import from_environment


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pubs.utils import add_pub



default_config = {
    'DB_URL': 'mongodb://localhost/pub_db',
    'MYSQL_HOST': 'localhost',
    'MYSQL_USER': None,
    'MYSQL_PASSWORD': None,
}
config = from_environment(default_config)

def cleanURL(url):
    url = url.strip()
    if 'http:// ' in url:
        url = 'http://'+url.replace('http:// ','').strip()
    if 'http :// ' in url:
        url = 'https://'+url.replace('http ://','').strip()
    return url

async def main():
    logging.info(f'DB: {config["DB_URL"]}')
    db_url, db_name = config['DB_URL'].rsplit('/', 1)
    logging.info(f'DB name: {db_name}')
    db = motor.motor_asyncio.AsyncIOMotorClient(db_url)[db_name]

    connection = pymysql.connect(host=config['MYSQL_HOST'],
                                 user=config['MYSQL_USER'],
                                 password=config['MYSQL_PASSWORD'],
                                 db='drupal_wipac',
                                 charset='utf8',
                                 cursorclass=pymysql.cursors.DictCursor)

    sql = """
select node.nid, node.title,
       a.field_authors_value as authors,
       ttt.name as pubtype,
       r.field_reference_value as citation,
       pd.field_pubdate_value as date
from node
join field_data_field_authors a on node.nid = a.entity_id
join field_data_field_pubtype pt on pt.entity_id = node.nid
join taxonomy_term_data ttt on ttt.tid = pt.field_pubtype_tid
join field_data_field_reference r on r.entity_id = node.nid
join field_data_field_pubdate pd on pd.entity_id = node.nid
where node.type = 'publication'
    """
    sql_downloads = 'select field_link_url as url from field_data_field_link l where l.entity_id = %s'
    sql_projects = 'select ttp.name as project from field_data_field_project p join taxonomy_term_data ttp on ttp.tid = p.field_project_tid where p.entity_id = %s'
    with connection.cursor() as cursor:
        cursor.execute(sql)
        data = cursor.fetchall()

        for row in data:
            title = row['title'].strip()
            authors = [row['authors'].strip()]
            type = row['pubtype'].strip().lower()
            if type == 'theses':
                type = 'thesis'
            elif type == 'conference proceeding':
                type = 'proceeding'
            elif type == 'journal article':
                type = 'journal'
            citation = row['citation'].strip()
            date = row['date'].isoformat()

            # improved date finding
            for part in reversed(citation.split(',')):
                try:
                    part = part.split(';',1)[0].split('-',1)[-1].strip()
                    date = datetime.strptime(part, "%d %B %Y").isoformat()
                    break
                except Exception:
                    continue

            cursor.execute(sql_downloads, (row['nid'],))
            row['downloads'] = [cleanURL(r['url']) for r in cursor.fetchall()]
            cursor.execute(sql_projects, (row['nid'],))
            row['projects'] = [r['project'] for r in cursor.fetchall()]

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
                    logging.info(f'skipping {row}')
                    logging.info(f'  already entered: {ret}')
                    continue
                else:
                    logging.info(f'bad entry {row}')
                    logging.info(f'  already entered: {ret}')
                    break
            logging.info(f'processing {title}')

            download = row['downloads']
            projects = [p.lower() for p in row['projects']]
            sites = []
            if projects == ['none']: # special case: this is Kael's pub
                print('NONE',title,type,authors,citation)
                projects = []
                sites = []
            elif 'icecube' in projects and 'wipac' in projects: # special case
                projects = ['icecube']
                sites = ['wipac']
            else:
                if projects: # any + other -> site=WIPAC
                    sites.append('wipac')
                if 'icecube' in projects:
                    sites.append('icecube')
                if 'other' in projects: # other is not a real project
                    projects = [x for x in projects if x != 'other']
                if 'wipac' in projects: # wipac is not a project
                    projects = [x for x in projects if x != 'wipac']
                if 'ara' in projects:
                    sites.append('ara')

            doc = {
                'title': title,
                'authors': authors,
                'pub_type': type,
                'citation': citation,
                'date': date,
                'downloads': download,
                'projects': projects,
                'sites': sites,
            }

            try:
                await add_pub(db, **doc)
            except AssertionError:
                logging.info(f'{doc}')
                raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())