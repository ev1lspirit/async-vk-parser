import ast
import asyncio
import os
import typing as tp
from json import JSONDecodeError
from typing import NamedTuple
import aiohttp


class API(NamedTuple):
    ACCESS_TOKEN = os.getenv("TOKEN")
    VERSION = 5.131


class DefaultRequestSettings(NamedTuple):
    ALL_FIELDS = "about,activities,occupation,bdate,city,connections,contacts,counters," \
                 "relatives,sex,universities,last_seen"


class Friends(NamedTuple, DefaultRequestSettings):
    REQUEST_LIMIT = 5

    @staticmethod
    def get(id_list, *, fields=DefaultRequestSettings.ALL_FIELDS, count=500):
        for user_id in id_list:
            yield rf"https://api.vk.com/method/friends.get?user_id={user_id}&count={count}&fields={fields}" \
                  rf"&access_token={API.ACCESS_TOKEN}&v={API.VERSION}"

    @staticmethod
    def get_mutual(target_list: tp.List[tp.Tuple[int, int]], count=500) -> tp.List[str]:
        for pair in target_list:
            if isinstance(pair, str):
                pair = ast.literal_eval(pair)
            source, target = pair
            yield rf"https://api.vk.com/method/friends.getMutual?source_uid={source}&target_uids={target}&count={count}&access_token={API.ACCESS_TOKEN}&v={API.VERSION}"


class AsyncRequest:
    def __init__(self, coroutine):
        self.coroutine = coroutine

    @staticmethod
    async def fetch_content(url, session):
        async with session.get(url) as client:
            if not client.ok:
                return
            try:
                json = await client.json()
            except JSONDecodeError as e:
                print(e)
                json = {}
            return json

    async def create_session(self, url_gen):
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in url_gen:
                tasks.append(self.fetch_content(url, session))
            result = await asyncio.gather(*tasks)
        return result

    async def run(self):
        return await self.create_session(self.coroutine)

    def run_loop(self):
        return asyncio.run(self.run())


if __name__ == "__main__":
    print(API.ACCESS_TOKEN)


