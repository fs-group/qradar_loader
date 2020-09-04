import os
import asyncio
import time
import signal
from asyncio import Event
import sys
import logging
import requests
import json
import aiohttp
from logging.handlers import RotatingFileHandler

sys.path.extend(['.', '../'])
from config import (FS_TI_URL, API_KEY, QRADAR_URL, LOAD_BULK,
                    QRADAR_TOKEN, INTERVAL, CHUNK_SIZE)


class Loader:

    def __init__(self, exit_event, log):
        self.exit_event = exit_event
        self.loop = asyncio.get_event_loop()
        self.start_time = time.time()
        self.log = log
        self.bulk_url = f'{QRADAR_URL}/bulk_load/fs_ti'
        self.single_url = f'{QRADAR_URL}/fs_ti'
        self.create_url = QRADAR_URL
        self.purge_url = f'{QRADAR_URL}/fs_ti?purge_only=true'

    @property
    def header(self):
        return {'SEC': QRADAR_TOKEN, 'Content-Type': 'application/json'}

    async def load_bulk_ips(self, idx, chunk):
        self.log.info(f'Thread {idx}. Load bulk. Size {len(chunk)}')

        data = json.dumps({x.get('ipv4'): x.get('ipv4')
                           for x in map(json.loads, chunk)})
        del chunk
        async with aiohttp.ClientSession(headers=self.header) as sess:
            async with sess.post(
                    self.bulk_url, data=data, ssl=False) as resp:
                if resp.status != 200:
                    self.log.error(f'Response status: {resp.status}. '
                                   f'Content: {resp.content.read()} '
                                   f'Headers: {resp.headers}')
        self.log.info(f'Thread {idx}. End load bulk.')

    async def load_single_ips(self, idx, data):
        self.log.info(f'Thread {idx}. Start load one by one. Size {len(data)}')

        def source(x):
            return f"category: {x.get('category')}, " \
                   f"comment: {x.get('comment')}, " \
                   f"criminal: {x.get('criminal')}, " \
                   f"country: {x.get('country')}, " \
                   f"cdn: {x.get('cdn')}"

        async with aiohttp.ClientSession(headers=self.header) as sess:
            for line in data:
                line = json.loads(line)
                data = f"?key={line.get('ipv4')}&value={line.get('ipv4')}" \
                       f"&source={source(line)}"
                async with sess.post(
                        self.single_url + data, ssl=False) as resp:
                    if resp.status != 200:
                        self.log.error(f'Response status: {resp.status}. '
                                       f'Content: {resp.content.read()} '
                                       f'Headers: {resp.headers}')
        self.log.info(f'Thread {idx}. End load one by one.')

    async def check_exists(self):
        async with aiohttp.ClientSession(headers=self.header) as sess:
            async with sess.get(self.create_url, ssl=False) as resp:
                if resp.status == 200:
                    self.log.info(f'Map "fsti" already exists.')
                    return
        self.log.info(f'Try create map "fsti".')
        async with aiohttp.ClientSession(headers=self.header) as sess:
            data = f'?element_type=IP&name=fsti'
            async with await sess.post(
                    self.create_url + data, ssl=False) as resp:
                if resp.status != 200:
                    self.log.error(f'Response status: {resp.status}. '
                                   f'Content: {resp.content.read()}'
                                   f'Headers: {resp.headers}')
        self.log.info(f'Created map "fsti".')

    async def purge_map(self):
        self.log.info(f'Try purge map "fsti".')
        async with aiohttp.ClientSession(headers=self.header) as sess:
            async with sess.delete(self.purge_url, ssl=False) as resp:
                if resp.status != 202:
                    self.log.error(f'Response status: {resp.status}. '
                                   f'Content: {resp.content.read()} '
                                   f'Headers: {resp.headers}')

        self.log.info(f'Purged map "fsti".')
        await asyncio.sleep(10)

    async def send(self, data):
        self.log.info(f'Available {len(data)} records for load')
        if not data:
            return
        self.log.info('Creating map...')
        tries = 5
        error = None
        while tries > 0:
            tries -= 1
            try:
                await self.check_exists()
                break
            except Exception as e:
                error = e
                await asyncio.sleep(5)
                continue
        else:
            self.log.error(
                f'Failed create map {self.create_url}. Error: {error}')
            return

        await self.purge_map()
        try:
            chunks = [data[x:x + CHUNK_SIZE] for x
                      in range(0, len(data), CHUNK_SIZE)]
            if LOAD_BULK:
                tasks = [asyncio.ensure_future(self.load_bulk_ips(idx, chunk))
                         for idx, chunk in enumerate(chunks)]
                await asyncio.gather(*tasks)
            else:
                tasks = [
                    asyncio.ensure_future(self.load_single_ips(idx, chunk))
                    for idx, chunk in enumerate(chunks)]
                await asyncio.gather(*tasks)
        except Exception as e:
            self.log.exception(e)

    async def work(self):
        while not self.exit_event.is_set():
            try:
                req = requests.get(
                    url=FS_TI_URL,
                    headers={'Api-Key': API_KEY,
                             'Content-Type': 'application/json'},
                    verify=False,
                    timeout=30)
                data_gen = [x for x in req.content.decode().split('\n') if x]
                await self.send(data_gen)
            except Exception as e:
                self.log.exception(f'Run error: {e}')
            if self.exit_event.is_set():
                break
            diff = int(time.time() - self.start_time)
            need = abs(INTERVAL - diff)
            self.log.info(f'Task completed for {diff}sec. '
                          f'Next run after {need}sec')
            while not self.exit_event.is_set() and need > 0:
                time.sleep(60)
                need -= 60

        self.log.info('Received exit event. Stopping...')

    def run(self):
        self.log.info(f'Started parser {self.__class__.__name__}')
        self.loop.run_until_complete(self.loop.create_task(self.work()))


if __name__ == '__main__':
    log_dir = os.path.join(os.path.dirname(__file__), './logs')
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)
    logger = logging.getLogger("loader")
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s  %(levelname)s  %(filename)s  %(lineno)s  %(message)s')
    log_file = os.path.join(log_dir, 'updater.log')
    handler = RotatingFileHandler(
        log_file, maxBytes=100 * 1024 * 1024, backupCount=5)
    stream = logging.StreamHandler()
    stream.setFormatter(formatter)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.addHandler(stream)

    ex_ev = Event()
    app = Loader(ex_ev, logger)


    def signal_handler(sig, frame):
        app.exit_event.set()


    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    app.run()
