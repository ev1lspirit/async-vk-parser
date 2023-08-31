import dataclasses
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


class ErrorCode(enum.Enum):
    EMPTY_COMMAND = 0x1
    COMMAND_NOT_FOUND = 0x2
    INCORRECT_COMMAND = 0x3


@dataclasses.dataclass
class CommandHandlingError:
    error_code: int
    error_message: str

    @property
    def json(self):
        return {
            "error": True,
            "code": self.error_code,
            "message": self.error_message}


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
        #print(result)
        # print(result)

    return result
