import pydantic as pd
import typing as tp

# ResponseType = tp.TypeVar('ResponseType', Friends)


class APIError(pd.BaseModel):
    error_code: int
    error_msg: str

    @property
    def error_json(self):
        return {"api_error_code": self.error_code, "error_msg": self.error_msg}


class City(pd.BaseModel):
    id: int
    title: str


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


class Profile(pd.BaseModel):
    id: int
    first_name: str
    last_name: str
    bdate: str = None
    city: City = None
    mobile_phone: str = None
    sex: int = None
    universities: tp.List[University] = None
    occupation: Occupation = None
    platform: str = None
    about: str = None
    deactivated: str = None
    is_closed: bool = False


class Friends(pd.BaseModel):
    items: tp.List[Profile]


class Response(pd.BaseModel):
    response: Friends = None
    error: APIError = None