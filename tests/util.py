import time
import asyncio
import socket
import os

import pytest
from rest_tools.server import from_environment
import motor.motor_asyncio

from pubs.server import create_server

@pytest.fixture
def port():
    """Get an ephemeral port number."""
    # https://unix.stackexchange.com/a/132524
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    addr = s.getsockname()
    ephemeral_port = addr[1]
    s.close()
    return ephemeral_port

@pytest.fixture
async def mongo_client():
    default_config = {
       'DB_URL': 'mongodb://localhost/pub_db',
    }
    config = from_environment(default_config)
    db = motor.motor_asyncio.AsyncIOMotorClient(config['DB_URL'])
    db_name = config['DB_URL'].split('/')[-1]
    ret = db[db_name]

    await ret.publications.drop()
    try:
        yield ret
    finally:
        await ret.publications.drop()

@pytest.fixture
async def server(monkeypatch, port, mongo_client):
    monkeypatch.setenv('DEBUG', 'True')
    monkeypatch.setenv('PORT', str(port))

    s = create_server()

    yield mongo_client, f'http://localhost:{port}'
    await s.stop()
