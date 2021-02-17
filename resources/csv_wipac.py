"""
Create CSV for WIPAC website
"""
import os
import sys
import asyncio
import logging
from datetime import datetime
from csv import DictWriter

import motor.motor_asyncio
import pymysql.cursors
from rest_tools.server import from_environment


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pubs.utils import add_pub



default_config = {
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

    fieldnames = ['nid','title','authors','pubtype','citation','date','downloads','projects']

    with open('wipac.csv', 'w', newline='') as csvfile:
        writer = DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        with connection.cursor() as cursor:
            cursor.execute(sql)
            data = cursor.fetchall()

            for row in data:
                logging.info(row['title'])
                cursor.execute(sql_downloads, (row['nid'],))
                row['downloads'] = [cleanURL(r['url']) for r in cursor.fetchall()]
                cursor.execute(sql_projects, (row['nid'],))
                row['projects'] = [r['project'] for r in cursor.fetchall()]
                writer.writerow(row)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())