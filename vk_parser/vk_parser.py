# -*- coding: utf8 -*-

import abc
import re
import typing as tp
import warnings
import heapq
from collections import defaultdict, Counter
from itertools import groupby
from operator import attrgetter
from exceptions import BadJSONError, ValidationError
from service_functions import ProfileTransformedList
from .pydantic_models import Response, Profile, Photo
from datetime import datetime


class OccupationType(tp.NamedTuple):
    UNIVERSITY = "university"
    WORK = "work"


class BaseParser(abc.ABC):

    def __init__(self, response_list: list[dict]):
        print(response_list)
        self.response = response_list
        self.response_items = (ProfileTransformedList(iterable=response.response.items) for response in self.response
                               if response.response is not None and response.response.items is not None)

    @property
    def response(self):
        return self._response

    @response.setter
    def response(self, response_list: list[dict]):
        if not response_list:
            raise ValueError("Empty response.")
        self._response = []
        for json_ in response_list:
            if not isinstance(json_, dict):
                raise BadJSONError(f"Expected type Iterable[dict], "
                                   f"got Iterable[{type(json_).__name__}] instead,\nitem={json_}")
            try:
                self._response.append(Response(**json_))
            except ValidationError as tb:
                warnings.warn(f"Validation error: {tb.json()}")

    @abc.abstractmethod
    def parse(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def group_by(self, *args, **kwargs):
        raise NotImplementedError


class GroupingField(tp.NamedTuple):
    CITY = "city"
    UNIVERSITY = "university"
    OCCUPATION = "occupation"
    PLATFORM = "platform"
    BDATE = "bdate"


class FriendsParser(BaseParser):

    def parse(self, *args, **kwargs):
        print(self.response)

        for items_list in self.response_items:
            for group, items in self.group_by(items_list, group_field=GroupingField.CITY):
                print(group)
                for i in items:
                    print(i)
                print()

    @staticmethod
    def _filter_valid_occupation(target_list: ProfileTransformedList):
        for profile in filter(lambda user: user.occupation, target_list):
            if profile.occupation.type == OccupationType.WORK:
                yield profile

    @staticmethod
    def _filter_valid_platforms(target_list: ProfileTransformedList):
        return filter(lambda user: user.last_seen and user.last_seen.platform, target_list)

    def group_by(self, target_list: ProfileTransformedList, *, group_field: str):
        """group_map is a dict that contains pairs of filters
        (to filter invalid or empty fields from Pydantic models) and key functions that are necessary for
         sorting Pydantic models & grouping them by defined field"""

        group_map: dict[str, tuple[tp.Generator, tp.Callable]]
        group_map = {
            GroupingField.CITY: (filter(lambda profile: profile.city, target_list),
                                 lambda profile: profile.city.title),
            GroupingField.BDATE: (filter(lambda profile: profile.bdate and profile.bdate.year is not None, target_list),
                                  lambda profile: (profile.bdate.year, profile.bdate.month)),
            GroupingField.PLATFORM: (self._filter_valid_platforms(target_list),
                                     lambda profile: profile.last_seen.platform),
            GroupingField.OCCUPATION: (self._filter_valid_occupation(target_list),
                                       lambda profile: profile.occupation.name)
        }
        field_generators = group_map.get(group_field, (None, None))
        if not all(field_generators):
            return ()
        filter_gen, key_func = field_generators
        if not key_func:
            return filter_gen

        for count, generator in groupby(sorted(filter_gen, key=key_func, reverse=True), key=key_func):
            yield count, generator

    @staticmethod
    def get_most_frequent_university(profile_list: tp.List[Profile], *, top_count=1) -> tp.Union[tuple, tuple[tuple[str, int]]]:
        universities_count: Counter = Counter()
        universities_map = defaultdict(set)

        for profile in profile_list:
            print(profile.occupation)
            unique_universities = set()
            if profile.universities:
                for university in profile.universities:
                    universities_map[university.id].add(university.name.strip())
                    unique_universities.add(university.id)

            if profile.occupation and profile.occupation.type == OccupationType.UNIVERSITY:
                if profile.occupation.id and profile.occupation.id not in unique_universities:
                    universities_map[profile.occupation.id].add(profile.occupation.name.strip())
                    unique_universities.add(profile.occupation.id)

            universities_count += Counter(unique_universities)

        if not universities_count:
            return ()

        if top_count == 1:
            university_id, count = max(universities_count.items(), key=lambda x: x[1])
            return (universities_map[university_id], count),

        top_count = top_count if top_count < len(universities_count) else len(universities_count)
        return tuple((universities_map[university_id], count) for university_id, count in
                     heapq.nlargest(top_count, iterable=universities_count.items(), key=lambda x: x[1]))

    @staticmethod
    def get_people_with_the_same_last_name(*, target_last_name: str, profile_list: tp.List[Profile]) -> tp.Iterable[Profile]:
        target_last_name = target_last_name.capitalize()
        regexp = re.compile(r"\b(\w+)(?:ov|ev|in|skiy|sky|iy|ova|eva|ina|skaya|aya)\b")
        last_name_matched = regexp.search(target_last_name)

        if not last_name_matched:
            return filter(lambda profile: profile.last_name == target_last_name, profile_list)

        last_name_root = last_name_matched.group(1)
        match_last_names = re.compile(rf'\b{last_name_root}(?:ov|ev|in|skiy|sky|iy|ova|eva|ina|skaya|aya)\b')
        return filter(lambda profile: match_last_names.search(profile.last_name), profile_list)

    @staticmethod
    def get_most_frequent_city(profile_list: tp.List[Profile]) -> tp.Optional[str]:
        cities_count = Counter(profile.city.title for profile in profile_list if isinstance(profile, Profile)
                               and profile.city)
        if not cities_count:
            return None
        return max(cities_count, key=lambda x: cities_count[x])


class PhotoParser(BaseParser):
    def parse(self, *args, **kwargs):
        for response in self.response:
            if not response.response:
                continue
            for date, tags in self.group_tags(response.response.items):
                print(date, ":")
                for tag in tags:
                    print(self.vk_link_maker(tag))
                print()

    @staticmethod
    def vk_link_maker(tag: Photo):
        return f"https://vk.com/photo{tag.owner_id}_{tag.id}"

    def group_by(self, *args, **kwargs):
        pass

    @staticmethod
    def group_tags(tags_list: list[Photo]):
        tags_list.sort(key=attrgetter('date'))
        return groupby(tags_list, key=lambda tag: datetime.fromtimestamp(tag.date).strftime("%d-%m-%Y"))



# https://vk.com/photo-129220469_456239106?tag=350850226
# https://vk.com/photo-<owner_id>_<id>?tag=
# 295465044


class ProfileParser(BaseParser):
    def parse(self, *args, **kwargs):
        pass

"abcdef"

if __name__ == "__main__":
     json = [{'response': {'count': 35, 'items': [{'id': 308247, 'bdate': '4.11', 'last_seen': {'platform': 7, 'time': 1693231058}, 'occupation': {'id': 157921309, 'name': 'ПАО СК "РОСГОССТРАХ"', 'type': 'work'}, 'track_code': 'd38dba5ecJ64ps7sz1Xh_2Tm12lElF5pweVct5lkmhQWA12Ra7kR_dyXmL_DAu2tYndvsBPjShuogDI', 'sex': 1, 'first_name': 'Tatyana', 'last_name': 'Peplova', 'can_access_closed': True, 'is_closed': False}, {'id': 478207, 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1693201023}, 'occupation': {'id': 28212376, 'name': 'Сеть клиник МЕДСИ', 'type': 'work'}, 'track_code': 'c274fd08_1DKenMbkCWtAHrdS-oZu63xRgdiv8C0AYANYaLOWT2eM_safx-QIf5RfUzzM07MuYMvYgw', 'sex': 1, 'first_name': 'Anastasia', 'last_name': 'Smol', 'can_access_closed': False, 'is_closed': True}, {'id': 553372, 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1693379656}, 'occupation': {'name': 'ГКБ №1 им. Н.И. Пирогова', 'type': 'work'}, 'track_code': 'b7507288WZsfkZjLYBk0juEnI2aNKogcEDmPzfxDGgFMEDd8Vc84-Cuimc01G2GN5babv9pdnG55XOE', 'sex': 1, 'first_name': 'Olga', 'last_name': 'Guseva', 'can_access_closed': True, 'is_closed': False}, {'id': 563662, 'bdate': '17.11.1983', 'city': {'id': 1, 'title': 'Moscow'}, 'about': '', 'activities': '', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 7, 'time': 1693379135}, 'occupation': {'id': 71204133, 'name': 'Клиника № 1 ВиТерра Беляево', 'type': 'work'}, 'universities': [{'chair': 73027, 'chair_name': 'Оториноларингологии', 'city': 1, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'faculty': 1464, 'faculty_name': 'Лечебный факультет', 'graduation': 2007, 'id': 330, 'name': 'РГМУ им. Н.И. Пирогова'}], 'relatives': [{'type': 'sibling', 'id': 132367497}], 'track_code': '8b2f4d868IxysnK6KSLF_qSzG9pSSIV-B-m0Rylmz1JZS8NkKVqR70OFfrQidZf-oSKjAwU_kQxujNo', 'sex': 1, 'first_name': 'Irina', 'last_name': 'Ruzanova', 'can_access_closed': True, 'is_closed': False}, {'id': 791877, 'bdate': '7.1', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 1, 'time': 1686658373}, 'occupation': {'id': 127818989, 'name': 'НИКИО имени Л.И. Свержевского', 'type': 'work'}, 'track_code': 'c60f49f2cUSjW653fOwlmLzkbQfXUO6S0VpRor1bbIVeFK9i3CwQJ8Flr3544CufvnXV3oAn-uC4Pz8', 'sex': 1, 'first_name': 'Maria', 'last_name': 'Polyaeva', 'can_access_closed': False, 'is_closed': True}, {'id': 1975952, 'bdate': '30.3', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 1, 'time': 1678633410}, 'occupation': {'id': 330, 'name': 'РГМУ', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 1}, 'track_code': '72b7bbd1oO-WrcQVNL3a5qEXUtBjt_yAOXpapfsTjgeJdRMQmRPBjK_Ol0o2v4W3lu3mGi3O_4BQHzTB', 'sex': 1, 'first_name': 'Olesya', 'last_name': 'Ageeva', 'can_access_closed': True, 'is_closed': False}, {'id': 2065504, 'bdate': '25.11.1986', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1693378248}, 'occupation': {'id': 330, 'name': 'РГМУ', 'type': 'university', 'graduate_year': 2009, 'country_id': 1, 'city_id': 1}, 'track_code': 'f148ee13KKRGE8FlNkWvOiGns7kVnhBSHyJLniPNHh0Kj-EFF9FJx3MhwmQ4RfwzE10Hc1vnE1J2RyX6', 'sex': 1, 'first_name': 'Ekaterina', 'last_name': 'Filippova', 'can_access_closed': False, 'is_closed': True}, {'id': 2349345, 'bdate': '24.6.1984', 'city': {'id': 85, 'title': 'Makhachkala'}, 'about': 'Уролог-андролог', 'activities': 'Урология; Андрология; Урогинекология; Эндоскопическая и лапароскопическая урология', 'mobile_phone': '+7988-775-70-03', 'home_phone': '+7988-423-03-03', 'last_seen': {'platform': 2, 'time': 1693375902}, 'occupation': {'name': 'РЖД-Медицина, г. Махачкала', 'type': 'work'}, 'universities': [{'city': 85, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumnus (Specialist)', 'education_status_id': 5, 'faculty': 154943, 'faculty_name': 'Лечебный факультет', 'graduation': 2007, 'id': 618, 'name': 'ДГМУ (бывш. ДГМА)'}, {'chair': 1282674, 'chair_name': ' Кафедра урологии', 'city': 2, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumnus (Specialist)', 'education_status_id': 5, 'faculty': 19924, 'faculty_name': 'Хирургический факультет', 'graduation': 2009, 'id': 41, 'name': 'СЗГМУ им. Мечникова (бывш. СПбГМА, СПбМАПО, ЛСГМИ) '}], 'relatives': [], 'track_code': '1519ca9d3ShHgWl_ZGtfTeRh-1b4e3oqwicd5MS85EBCYm58QeC8S37gaX1iYw9J1ptPnLYCeSqrQnOA', 'sex': 2, 'first_name': 'Godzho', 'last_name': 'Guseynov', 'can_access_closed': True, 'is_closed': False}, {'id': 2468368, 'bdate': '27.12.1987', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1693330989}, 'occupation': {'id': 127818989, 'name': 'НИКИО имени Л.И. Свержевского', 'type': 'work'}, 'track_code': '4fabc7c1Sy3tVC1xb_J7hPJwfXz1L2gF4xx1N9wgksM0by9dqsgqTt5kJyNtr32AworJtrtWawWKeRtT', 'sex': 1, 'first_name': 'Nadezhda', 'last_name': 'Rezakova', 'can_access_closed': True, 'is_closed': False}, {'id': 2636985, 'bdate': '14.11', 'city': {'id': 1, 'title': 'Moscow'}, 'skype': 'meliora_spero_', 'last_seen': {'platform': 4, 'time': 1693212396}, 'occupation': {'name': 'ООО Медицинский центр "НЕБОЛИТ"', 'type': 'work'}, 'track_code': 'cba3bfc4yfot5iNTRRpYNu0bVJaeaRbQFi5Po4RB2cPEPdum7i-omR3QKVEVHlQ70eHgXNAQFdB_SyHH', 'sex': 1, 'first_name': 'Olga', 'last_name': 'Myskina', 'can_access_closed': True, 'is_closed': False}, {'id': 2661346, 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1693377053}, 'occupation': {'id': 668, 'name': 'НГМУ (НГМА)', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 99}, 'track_code': 'adcdf15f0Cnsj0FZAWMaJdLz0dbgMGrkLFtLjOTmd_T82NytrDuxSty7RAwBMxF07gllHK5JaeRFPiXo', 'sex': 1, 'first_name': 'Anastasia', 'last_name': 'Samkova', 'can_access_closed': True, 'is_closed': False}, {'id': 4768210, 'city': {'id': 35, 'title': 'Veliky Novgorod'}, 'last_seen': {'platform': 2, 'time': 1693395156}, 'occupation': {'id': 330, 'name': 'РГМУ им. Н.И. Пирогова', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 1}, 'track_code': '6bf753feOMh7SB1B2xcOi6E6l9WIJKcTMOr4N7T1nVgNB9BJxU1Zq095H0faG1nYmsAjH8ZdpBNZj5ZT', 'sex': 1, 'first_name': 'Elena', 'last_name': 'Shestakova', 'can_access_closed': True, 'is_closed': False}, {'id': 4810918, 'bdate': '27.9.1979', 'city': {'id': 1, 'title': 'Moscow'}, 'mobile_phone': 'нет', 'home_phone': 'нет', 'last_seen': {'platform': 4, 'time': 1693382477}, 'occupation': {'id': 243, 'name': 'МГМСУ', 'type': 'university', 'graduate_year': 2005, 'country_id': 1, 'city_id': 1}, 'track_code': '7f4a64feiYOmX_NTHo3ZbBYRxl3ZwJRcD709KpA6pjy7jNqla9zo4MA98lpL3tU4Iutyl5e5l1xm2FNO', 'sex': 2, 'first_name': 'Oleg', 'last_name': 'Vorontsoff', 'can_access_closed': True, 'is_closed': False}, {'id': 4959171, 'city': {'id': 148, 'title': 'Ulan-Ude'}, 'about': 'Врачую тела и души . Вселяю веру , надежду , любовь . Мотивирую .', 'activities': 'Врач сурдолог оториноларинголог . Психолог', 'last_seen': {'platform': 2, 'time': 1693132583}, 'occupation': {'id': 583, 'name': 'КрасГМУ (бывш. КГМА, КГМИ)', 'type': 'university', 'graduate_year': 2006, 'country_id': 1, 'city_id': 73}, 'universities': [{'chair': 42011, 'chair_name': 'Лечебного дела', 'city': 73, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumna (Specialist)', 'education_status_id': 5, 'faculty': 2102, 'faculty_name': 'Лечебный факультет', 'graduation': 2006, 'id': 583, 'name': 'КрасГМУ (бывш. КГМА, КГМИ)'}, {'chair': 73027, 'chair_name': ' Кафедра оториноларингологии', 'city': 1, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumnus (Specialist)', 'education_status_id': 5, 'faculty': 1464, 'faculty_name': 'Лечебный факультет', 'graduation': 2008, 'id': 330, 'name': 'РНИМУ (бывш. РГМУ) им. Н. И. Пирогова'}], 'relatives': [], 'track_code': 'efd630bayoDYyRerB4ksWO9JHBtwn2rlUcvMaNitaECBFnOJjISr47urEqoEgH8L07Oo0T7maeU4rqIM', 'sex': 1, 'first_name': 'Larisa', 'last_name': 'Sangadzhieva', 'can_access_closed': True, 'is_closed': False}, {'id': 6331371, 'bdate': '24.3.1974', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 1, 'time': 1637395337}, 'occupation': {'id': 179462, 'name': 'ДГМА', 'type': 'university', 'graduate_year': 2007, 'country_id': 0, 'city_id': 0}, 'track_code': 'd1808f23xIrjSKCX4Kt74wQO9Nr4NUuwJlOXJ6RxRc8wWz0i0L2l6dEq8pXgq3uwO_RAELZMSLBPNvlD', 'sex': 2, 'first_name': 'Saypudin', 'last_name': 'Abdurakhmanov', 'can_access_closed': True, 'is_closed': False}, {'id': 6426214, 'bdate': '24.4', 'city': {'id': 1, 'title': 'Moscow'}, 'occupation': {'id': 264, 'name': 'МГУС / РГУТиС (бывш. МТИ)', 'type': 'university', 'graduate_year': 2006, 'country_id': 1, 'city_id': 1}, 'track_code': 'c8b17774Gfvl7A7_wMv54npzXR-vQJpt4qXAENQuedpP7n_awt54mIGIDv_HyvKwQYnp1eE5mW2LwK50', 'sex': 1, 'deactivated': 'banned', 'first_name': 'Diana', 'last_name': 'Gadzhieva', 'can_access_closed': True, 'is_closed': False}, {'id': 7027938, 'bdate': '28.6.1988', 'city': {'id': 134, 'title': 'Stavropol'}, 'last_seen': {'platform': 7, 'time': 1332369803}, 'track_code': '02c51796hWgQR7cKpBxYJFRMRPt12QgBi6tyyu-lDtbpX-PzG3_kC3N1uAqkSldyfLbwMTugCwHizhyu', 'sex': 2, 'first_name': 'Akhmed', 'last_name': 'Aliev', 'can_access_closed': True, 'is_closed': False}, {'id': 7216695, 'bdate': '25.6.1984', 'city': {'id': 85, 'title': 'Makhachkala'}, 'about': '', 'activities': '', 'last_seen': {'platform': 2, 'time': 1557758259}, 'occupation': {'name': 'гкг мвд россии', 'type': 'work'}, 'universities': [{'city': 85, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Postgraduate Student', 'education_status_id': 8, 'faculty': 154943, 'faculty_name': 'Лечебный факультет', 'graduation': 2007, 'id': 618, 'name': 'ДГМА\r\n'}], 'relatives': [], 'track_code': 'a27e4d42dIn1d3SFbsd7PrDce8Bel6Wu_VxyQfmJ8A-QEY0xCK8V6pATIodoxiw_lCbPChDupq6UORwl', 'sex': 2, 'first_name': 'Murad', 'last_name': 'Izmailov', 'can_access_closed': True, 'is_closed': False}, {'id': 9359077, 'bdate': '7.9.1984', 'city': {'id': 1449, 'title': 'Budennovsk'}, 'about': '', 'activities': '', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 2, 'time': 1693382865}, 'occupation': {'id': 797, 'name': 'СГАУ (бывш. СИМСХ) им. Вавилова', 'type': 'university', 'graduate_year': 2010, 'country_id': 1, 'city_id': 125}, 'universities': [{'chair': 414322, 'chair_name': 'Экономика', 'city': 125, 'country': 1, 'education_form': 'Distance Learning', 'education_form_id': 3, 'education_status': 'Student (Specialist)', 'education_status_id': 2, 'graduation': 2010, 'id': 797, 'name': 'СГАУ (бывш. СИМСХ) им. Вавилова'}], 'relatives': [], 'track_code': 'ded1b14bRKrW2a8TQJlOd1lw5hs-OCo8u9ccaH1W3cRCbdyUAtQlyeK680YWlR8ifIpS0XBBKTzSsnIM', 'sex': 2, 'first_name': 'Avg', 'last_name': 'Alg', 'can_access_closed': True, 'is_closed': False}, {'id': 14814043, 'bdate': '20.1.1989', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1687323250}, 'track_code': '46120199anuoJ0YYR4Y0gdmL8GndT_M-Ohq_JM-3PGajIgF6sLkLGMkbER0ehDWB_kQvr4Av_ikhf9FAvA', 'sex': 1, 'first_name': 'Alexey', 'last_name': 'Krylov', 'can_access_closed': False, 'is_closed': True}, {'id': 19719802, 'city': {'id': 1, 'title': 'Moscow'}, 'about': '', 'activities': '', 'last_seen': {'platform': 7, 'time': 1644854691}, 'occupation': {'id': 330, 'name': 'РГМУ им. Н.И. Пирогова', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 1}, 'universities': [{'chair': 73027, 'chair_name': 'Оториноларингологии', 'city': 1, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumna (Specialist)', 'education_status_id': 5, 'faculty': 1464, 'faculty_name': 'Лечебный факультет', 'graduation': 2007, 'id': 330, 'name': 'РГМУ им. Н.И. Пирогова'}], 'relatives': [], 'track_code': 'e9111e91TE9ob5vGBlq3eWgWtmTLp0QhVmBpjn_7HVY-YMaChl4tLF4GnckHU7dxTNhpopbHSTZNBQfqDA', 'sex': 1, 'first_name': 'Marina', 'last_name': 'Yushkina', 'can_access_closed': True, 'is_closed': False}, {'id': 20648758, 'last_seen': {'platform': 4, 'time': 1678222408}, 'occupation': {'id': 330, 'name': 'РГМУ', 'type': 'university', 'graduate_year': 2010, 'country_id': 1, 'city_id': 1}, 'track_code': 'c2872bc5RluCcT7qmLR1bc96oXcUOdJU3YmTGcEZzn9evfAxWqMnOLRObeOa4n1u775-sUlZ30PG7P19sg', 'sex': 1, 'first_name': 'Valeria', 'last_name': 'Utesheva', 'can_access_closed': True, 'is_closed': False}, {'id': 28561662, 'bdate': '19.9.1983', 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 4, 'time': 1690194123}, 'occupation': {'name': 'ГКБ', 'type': 'work'}, 'track_code': 'fdc5aa92-6sR3EEXYGkaSg7DgLvS9rQVPURc9kLkeQSKHwZTO2KayCnkRhhmPRIYLg1ffY-WuQImITKSMQ', 'sex': 2, 'first_name': 'Vagab', 'last_name': 'Gadzhimuradov', 'can_access_closed': False, 'is_closed': True}, {'id': 51932333, 'bdate': '16.8', 'city': {'id': 1, 'title': 'Moscow'}, 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 1, 'time': 1693351160}, 'occupation': {'name': 'ГБУЗ ГП № 23', 'type': 'work'}, 'track_code': '03eb567ddYApe_gjAxjU4NJg-DKPtZrOwJoiYS_C5YEFKIiLvjYU4x1FriRbGICx9q8n9NLVl9nb_0wFXA', 'sex': 1, 'first_name': 'Naida', 'last_name': 'Babaeva', 'can_access_closed': True, 'is_closed': False}, {'id': 52663084, 'city': {'id': 85, 'title': 'Makhachkala'}, 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 2, 'time': 1693336313}, 'occupation': {'id': 618, 'name': 'ДГМА\r\n', 'type': 'university', 'graduate_year': 2009, 'country_id': 1, 'city_id': 85}, 'lists': [27], 'track_code': '1afc1e4cRZzNnFod8FWEWJS0NRfGUXfkdYoI1jp0HxsQhDA7pQQz-8L0CRerB9lshH3eisx7Ia4o6QvTO0AWAGPwb1g', 'sex': 2, 'first_name': 'Gadzhi', 'last_name': 'Gasanov', 'can_access_closed': True, 'is_closed': False}, {'id': 62984844, 'city': {'id': 85, 'title': 'Makhachkala'}, 'about': '-----', 'activities': 'врач-невролог', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 7, 'time': 1293461323}, 'occupation': {'id': 618, 'name': 'ДГМА\r\n', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 85}, 'universities': [{'city': 85, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumna (Specialist)', 'education_status_id': 5, 'faculty': 154943, 'faculty_name': 'Лечебный факультет', 'graduation': 2007, 'id': 618, 'name': 'ДГМА\r\n'}], 'relatives': [], 'track_code': 'f86f5f2b_meRtKpr6I-NOeSQUnPJbUpCxea9jW6Tv9S110963yGfBPffrmHjgYBiyViNtZQNR1Xeg9PpHQ', 'sex': 1, 'first_name': 'Uma', 'last_name': 'Aygumova', 'can_access_closed': True, 'is_closed': False}, {'id': 83160738, 'bdate': '5.9', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 7, 'time': 1324245036}, 'occupation': {'id': 618, 'name': 'ДГМА\r\n', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 85}, 'track_code': '1a27dd0cdK5E5MjSpUCZ-DykH3eCh-hi4cz24bi5T85IyGps-o0VzSePlIWjEJr4FWDAsd_n5XX6qZiFyw', 'sex': 1, 'first_name': 'Naida', 'last_name': 'Gadgieva', 'can_access_closed': True, 'is_closed': False}, {'id': 95570300, 'bdate': '24.9.1984', 'city': {'id': 1, 'title': 'Moscow'}, 'about': '', 'activities': '', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 4, 'time': 1693304184}, 'occupation': {'id': 215, 'name': 'Первый МГМУ им. И.М. Сеченова (бывш. ММА им. Сеченова)', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 1}, 'universities': [{'city': 1, 'country': 1, 'education_form': 'Full-time', 'education_form_id': 1, 'education_status': 'Alumnus (Specialist)', 'education_status_id': 5, 'faculty': 849, 'faculty_name': 'Лечебный факультет', 'graduation': 2007, 'id': 215, 'name': 'Первый МГМУ им. И.М. Сеченова (бывш. ММА им. Сеченова)'}], 'relatives': [], 'track_code': '9c7e661esjnP_K91HtVXDa_eJIquLoCfpySn1mJhqAjFZkaI13PTWq3G9XEa0FMIhBL7TPNOjYi8QcmyEQ', 'sex': 2, 'first_name': 'Alexander', 'last_name': 'Nikitkin', 'can_access_closed': True, 'is_closed': False}, {'id': 103811319, 'bdate': '20.8', 'city': {'id': 85, 'title': 'Makhachkala'}, 'occupation': {'id': 618, 'name': 'ДГМА\r\n', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 85}, 'track_code': 'd273d5ffj0BMuPJ9RD6r0WmmUqTRXlA1f5W5ag95KSxw68IQKA_uI3vTpSxEP67YRmuyCYAtRCxzgtcOfCY', 'sex': 1, 'deactivated': 'deleted', 'first_name': 'Elya', 'last_name': 'Magomedova', 'can_access_closed': True, 'is_closed': False}, {'id': 114817417, 'bdate': '17.3', 'mobile_phone': '...', 'home_phone': '...', 'last_seen': {'platform': 4, 'time': 1692023315}, 'track_code': 'c55ab238C5cOP390EuGfglgLiKrljvzIk1kEnmr9ojaBH9GXN3Nq9DlVen1AupiMccZmB7T96NGfTmr6GaI', 'sex': 1, 'first_name': 'Dzhamilya', 'last_name': 'Kurbanova', 'can_access_closed': True, 'is_closed': False}, {'id': 137333418, 'city': {'id': 1, 'title': 'Moscow'}, 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 1, 'time': 1449686573}, 'occupation': {'id': 618, 'name': 'ДГМА\r\n', 'type': 'university', 'country_id': 1, 'city_id': 85}, 'track_code': 'b0ce0978YewpBrot3hGUn4-jRIBfL5r7ZKJnBXEOINS3GLMDZtkAj0w2vSyIR5LPpW6lLQ5cjuJotQlhAlE', 'sex': 2, 'first_name': 'Takhir', 'last_name': 'Gammaev', 'can_access_closed': True, 'is_closed': False}, {'id': 145125619, 'city': {'id': 1, 'title': 'Moscow'}, 'last_seen': {'platform': 2, 'time': 1693384140}, 'lists': [25], 'track_code': '3fe6a2bdQnHh6TC6taPOuVYGPckuxTz1DE1WfnVXxHxBhx1KgOY0FrqHZrXspp2OQMvQVyPub7FUET53Z3rDcEDzQin1', 'sex': 1, 'first_name': 'Uma', 'last_name': 'Aygumova', 'can_access_closed': False, 'is_closed': True}, {'id': 173271574, 'city': {'id': 85, 'title': 'Makhachkala'}, 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 2, 'time': 1447075777}, 'occupation': {'id': 618, 'name': 'ДГМА\r\n', 'type': 'university', 'graduate_year': 2007, 'country_id': 1, 'city_id': 85}, 'track_code': 'a433e311k3uklqyTlUhcJ_oalD26ceb_vAEg_bbLjbk8VxFSquXyGMWorpSVSF4n79F5kOsC8uawFk6ZxZQ', 'sex': 2, 'first_name': 'Magomedali', 'last_name': 'Salamov', 'can_access_closed': True, 'is_closed': False}, {'id': 326866720, 'bdate': '18.5.1979', 'about': '', 'activities': '', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 4, 'time': 1654370383}, 'universities': [], 'relatives': [], 'track_code': '8a9d032dANLL34mxLhzouYpWEp8uyTT-gKmhfggDfZ0blj7EgCJhsann27F5R-a3nJj7Mn-6IOeMvs8ae1w', 'sex': 1, 'first_name': 'Marina', 'last_name': 'Alieva', 'can_access_closed': True, 'is_closed': False}, {'id': 501763242, 'city': {'id': 99, 'title': 'Novosibirsk'}, 'about': '', 'activities': '', 'mobile_phone': '', 'home_phone': '', 'last_seen': {'platform': 2, 'time': 1686394456}, 'occupation': {'id': 173811553, 'name': 'Обучение вышивке и росписи | в рамках приличия', 'type': 'work'}, 'universities': [], 'relatives': [], 'track_code': '046b3e67hRRRKTtgRt5NGJWv9OOXIPtU4dIEDHJ19Rb4_Ms_PKnkd2NDOWgUjU5IhWcfTsZT703txWpoASo', 'sex': 1, 'first_name': 'Sofia', 'last_name': 'Solovina', 'can_access_closed': True, 'is_closed': False}]}}]
  #  parser = FriendsParser(json)
   # print(parser.parse())


