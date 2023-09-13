import pydantic as pd
import typing as tp


class APIError(pd.BaseModel):
    error_code: int
    error_msg: str
    details: tp.Optional[str] = None

    @property
    def error_json(self):
        return {"api_error_code": self.error_code, "error_msg": self.error_msg}


class City(pd.BaseModel):
    id: int
    title: str


class Photo(pd.BaseModel):
    album_id: int
    date: int
    id: int
    owner_id: int
    post_id: int = None
    text: tp.Optional[str] = None
    tags_count: tp.Optional[int] = None


class Photos(pd.BaseModel):
    items: tp.List[Photo]


class Occupation(pd.BaseModel):
    name: str
    type: str
    id: int = None


class University(pd.BaseModel):
    id: int = None
    chair_name: str = None
    city: int = None
    education_form: str = None
    education_status: str = None
    faculty: int = None
    faculty_name: str = None
    graduation: int = None
    name: str = None
    valid_record = True


class LastSeenEntity(pd.BaseModel):
    time: tp.Optional[int]
    platform: tp.Optional[int] = None


class Profile(pd.BaseModel):
    id: int
    first_name: str
    last_name: str
    last_seen: LastSeenEntity = None
    bdate: str = None
    city: City = None
    mobile_phone: str = None
    sex: int = None
    universities: tp.List[University] = []
    occupation: tp.Optional[Occupation] = None
    platform: str = None
    about: str = None
    deactivated: str = None
    is_closed: bool = False


class Friends(pd.BaseModel):
    items: list[Profile]


EntityType = tp.TypeVar("EntityType", Friends, Photos)


class Response(pd.BaseModel):
    response: tp.Optional[EntityType] = None
    error: tp.Optional[APIError] = None