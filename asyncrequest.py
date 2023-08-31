import asyncio
import typing as tp
from aiohttp import (
    ClientResponseError,
    ClientPayloadError,
    ClientConnectorError,
)
from json import JSONDecodeError
import aiohttp
from config import form_error_json


class AsyncRequest:
    def __init__(self, coroutine):
        self.coroutine = coroutine

    @staticmethod
    async def fetch_content(url, session):
        try:
            async with session.get(url) as client:
                if not client.ok:
                    raise ClientResponseError(
                        client.request_info,
                        client.history,
                        status=client.status)
                json: dict = await client.json()

        except ClientResponseError as traceback:
            return form_error_json(error_code=traceback.status,
                                   error_message=f"An error occurred while fetching url: {url}: {str(traceback)}",
                                   details=f"Server responded with an error status.")
        except ClientPayloadError:
            return form_error_json(error_code=0,
                                   error_message=f"Invalid payload",
                                   details=f"Could not read or process the response payload for {url}")
        except ClientConnectorError as traceback:
            return form_error_json(error_code=traceback.errno,
                                   error_message=traceback.strerror,
                                   details=f"Could not connect to {url}")
        except TimeoutError:
            return form_error_json(error_code=0,
                                   error_message=f"Timeout",
                                   details=f"The request or response took too long for {url}")
        except JSONDecodeError:
            return client.text()
        return json

    async def create_session(self, url_gen):
        async with aiohttp.ClientSession() as session:
            tasks = [self.fetch_content(url, session) for url in url_gen]
            result = await asyncio.gather(*tasks)
        return result

    async def run(self) -> tp.List[dict]:
        return await self.create_session(self.coroutine)

    def run_loop(self):
        return asyncio.run(self.run())


if __name__ == "__main__":
    pass

