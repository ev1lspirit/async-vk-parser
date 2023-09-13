import enum
import re

from config import (
    CommandType,
    FriendsAPI,
    form_error_json
)
import typing as tp
from exceptions import (
    EmptyCommandError,
    IncorrectCommandError,
    CommandNotFoundError
)
from asyncrequest import AsyncRequest
from representation_functions import StaticResponse
from vk_parser.pydantic_models import Profile, Photo, EntityType


class ErrorCode(enum.Enum):
    EMPTY_COMMAND = 0x1
    COMMAND_NOT_FOUND = 0x2
    INCORRECT_COMMAND = 0x3


class Commands(tp.NamedTuple):
    HELP = "help"
    FRIENDS = "friends"
    EXIT = "exit"
    ISMUTUAL = "ismutual"


message_map: tp.Dict[str, tp.Callable] = {
    Commands.HELP: StaticResponse.help,
    Commands.FRIENDS: FriendsAPI.get,
    Commands.ISMUTUAL: FriendsAPI.get_mutual
}


def parse_command(message) -> CommandType:
    """Parses a message into a command type.
        Args: message: The message to parse.

        Returns: A command type object that contains the command function or coroutine and the arguments.

        Raises: EmptyCommandError: If the message is empty.
                IncorrectCommandError: If the message does not match the expected pattern.
                CommandNotFoundError: If the message does not contain a valid command.
    """
    print(message)
    if not message.strip():
        raise EmptyCommandError("[-] Command is empty!")
    command = re.search(r"^(help|friends(\s+\d+){1,5}|ismutual(\s+\(\d+,\d+\)){1,5})$", message)
    if not command:
        raise IncorrectCommandError(message)
    parts = command.group().split()
    print(parts)
    command = parts.pop(0)
    return CommandType(command, parts)


async def execute_command(message: str) -> dict:
    """Executes a message as a command.
     Args: message: The message to execute.

     Returns: A string or a dictionary that represents the result of the command.
            """
    try:
        command: CommandType = parse_command(message)
    except EmptyCommandError as traceback:
        return form_error_json(error_code=ErrorCode.EMPTY_COMMAND.value, error_message=str(traceback))
    except CommandNotFoundError as traceback:
        print("here")
        return form_error_json(error_code=ErrorCode.COMMAND_NOT_FOUND.value,
                               error_message=f"[-] No such command: {str(traceback)}:" \
               f'\n To get a list of available commands, type "help"')
    except IncorrectCommandError as traceback:
        return form_error_json(error_code=ErrorCode.INCORRECT_COMMAND.value,
                               error_message=f"[-] Incorrect command: \n {str(traceback)} is not a valid expression. " \
               f'\n To get a list of available commands, type "help"')

    command_head, command_args = command.command, command.args
    if command_head == Commands.HELP:
        executable = message_map[Commands.HELP]
        result = executable(command_args)
    else:
        coroutine = message_map[command_head]
        request = AsyncRequest(coroutine(command_args))
        result = await request.run()

    return result


class BirthDate(tp.NamedTuple):
    day: int
    month: int
    year: tp.Optional[int] = None


class BaseDataTransformer:
    def __init__(self, *, iterable: tp.Iterable[EntityType]):
        self.iterable = iterable

    @property
    def iterable(self):
        return self._iterable

    @iterable.setter
    def iterable(self, iterable):
        if not iterable:
            raise ValueError('Empty iterable')

        for element in iterable:
            if not isinstance(element, (Profile, Photo)):
                raise ValueError(f"Expected Iterable[EntityType], got {type(element).__name__} instead")
        self._iterable = iterable


class ProfileTransformedList(BaseDataTransformer):

    @BaseDataTransformer.iterable.setter
    def iterable(self, iterable):
        method_list = filter(lambda func:
                             callable(getattr(self, func)) and not func.startswith("__"), dir(self))
        for method in method_list:
            getattr(self, method)(iterable)
        super(ProfileTransformedList, ProfileTransformedList).iterable.__set__(self, iterable)

    def __iter__(self):
        yield from self.iterable

    @staticmethod
    def _parse_birth_date(target_list: list[Profile]):
        pattern = re.compile(r"^(\d{1,2})[.-](\d{1,2})[.-](\d\d\d\d)$")

        for profile in filter(lambda user: user.bdate is not None, target_list):
            result = pattern.search(profile.bdate)
            if result:
               profile.bdate = BirthDate(*(int(value) for value in result.groups()))
            else:
               profile.bdate = BirthDate(*(int(value) for value in re.split(r'[\.-]', profile.bdate)))

    @staticmethod
    def _parse_platform(target_list: list[Profile]):
        platforms = {
            1: "VK Mobile version",
            2: "Apple iPhone",
            3: "Apple iPad",
            4: "Android",
            5: "Windows Phone",
            6: "Windows 10",
            7: "PC Web version"
        }
        for profile in filter(lambda user: user.last_seen and user.last_seen.platform, target_list):
            profile.last_seen.platform = platforms.get(profile.last_seen.platform, None)



