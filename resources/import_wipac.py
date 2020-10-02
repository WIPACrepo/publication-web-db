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
            ret = await db.publications.find_one({'title': title})
            if ret:
                logging.info(f'skipping {title}')
                continue
            logging.info(f'processing {title}')

            cursor.execute(sql_downloads, (row['nid'],))
            row['downloads'] = [r['url'] for r in cursor.fetchall()]
            cursor.execute(sql_projects, (row['nid'],))
            row['projects'] = [r['project'] for r in cursor.fetchall()]

            authors = [row['authors'].strip()]
            type = row['pubtype'].strip().lower()
            if type == 'theses':
                type = 'thesis'
            elif type == 'conference proceeding':
                type = 'proceeding'
            elif type == 'journal article':
                type = 'journal'
            citation = row['citation'].strip()
            download = row['downloads']
            try:
                c, d = citation.rsplit(',', 1)
                d = d.strip()
                if '-' in d:
                    d = d.split('-')[0]+' '+d.split(' ',1)[-1]
                date = datetime.strptime(d.strip(), "%d %B %Y").isoformat()
                citation = c.strip()
            except ValueError:
                date = row['date'].isoformat()
            except Exception:
                raise
            projects = [p.lower() for p in row['projects']]
            if projects == ['none']:
                projects = ['other']

            doc = {
                'title': title,
                'authors': authors,
                'pub_type': type,
                'citation': citation,
                'date': date,
                'downloads': download,
                'projects': projects,
            }

            try:
                await add_pub(db, **doc)
            except AssertionError:
                logging.info(f'{doc}')
                raise

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())