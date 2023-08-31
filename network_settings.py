import dataclasses


@dataclasses.dataclass
class ExternalServerError:
    error_code: int
    error_message: str
    details: str

    @property
    def json(self):
        return {
            "error": True,
            "code": self.error_code,
            "message": self.error_message,
            "details": self.details}


@dataclasses.dataclass
class ExternalServerResponse:
    data: dict

