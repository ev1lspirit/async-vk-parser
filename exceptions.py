from pydantic import ValidationError

__all__ = ["BadJSONError", "EmptyCommandError",
           "IncorrectCommandError", "ValidationError",
           "CommandNotFoundError"]


class BadJSONError(Exception):
    pass


class EmptyCommandError(Exception):
    pass


class IncorrectCommandError(Exception):
    pass


class CommandNotFoundError(Exception):
    pass