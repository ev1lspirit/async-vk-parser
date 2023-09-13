from vk_parser import vk_parser
from asyncrequest import AsyncRequest
from config import Photos, FriendsAPI
import asyncio


# 672706393, 350850226,
async def run_main():
   request = AsyncRequest(FriendsAPI.get([295465044, 203663240, 551662769]))
   result = await request.run()

   for res in result:
      print(res)

   b = vk_parser.FriendsParser(result)
   print(b.parse())
   #a = vk_parser.PhotoParser(result)
   #print(a.parse())


if __name__ == "__main__":
   # server = AsyncServer.bind(ip="localhost", port=9090)
   # server.listen()
   asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
   asyncio.run(run_main())




