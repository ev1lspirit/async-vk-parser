import os
import typing as tp
import ast
import collections


CommandType = collections.namedtuple("Command", ["command", "args"])


def form_error_json(*, error_code, error_message, details=None) -> dict:
    response = {"error_code": error_code, "error_msg": error_message}
    if details:
        response["details"] = details
    return response


class API(tp.NamedTuple):
    ACCESS_TOKEN = os.getenv("TOKEN")
    VERSION = 5.131


class DefaultRequestSettings(tp.NamedTuple):
    ALL_FIELDS = "about,activities,occupation,bdate,city,platform,connections,contacts,counters," \
                 "relatives,sex,universities,last_seen"


class FriendsAPI:

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


class Photos:

    @staticmethod
    def get_user_photos(*, target_list: tp.List, count: int = 100, extended=0):
        for user_id in target_list:
            yield rf"https://api.vk.com/method/photos.getUserPhotos?user_id={user_id}&count={count}&extended={extended}\
            &access_token={API.ACCESS_TOKEN}&v={API.VERSION}"

