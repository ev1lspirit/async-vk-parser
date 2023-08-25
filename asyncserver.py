import collections
import socket
import asyncio
import typing as tp
import re
from asyncrequest import AsyncRequest, Friends


class Response:

    @staticmethod
    def greetings(ip_address):
        return f"Hi, {ip_address}. This is simple asynchronous server. Type 'help' to know what this server can do."

    @staticmethod
    def help():
        return f"\n---------------------------------\n~ 'echo' -\t command enables echo mode: server sends back your message" \
               f'\n~ "friends <VK id or username>" -\t returns a list of VK friends of a particular id' \
               f"\n~ 'ismutual <id1> <id2>' -\t returns a list of mutual friends between two users\n"


class Commands(tp.NamedTuple):
    HELP = "help"
    FRIENDS = "friends"
    EXIT = "exit"
    ISMUTUAL = "ismutual"


Command = collections.namedtuple("Command", ["command", "args"])
Coroutine = collections.namedtuple("Coroutine", "generator")
Function = collections.namedtuple("Function", "func_obj")

message_map: tp.Dict[str, Command] = {
    Commands.HELP: Function(Response.help),
    Commands.FRIENDS: Coroutine(Friends.get),
    Commands.ISMUTUAL: Coroutine(Friends.get_mutual)
}


def parse_command(message) -> Command:
    if not message:
        raise ValueError("Command is empty!")
    pattern = re.compile(r"^(help|friends(\s+\d+){1,5}|ismutual(\s+\(\d+,\d+\)){1,5})$")
    command = re.search(pattern, message)
    if not command:
        raise ValueError("Incorrect command given.")
    parts = command.group().split()
    print(parts)
    command = parts.pop(0)
    exist_command = message_map.get(command, None)
    if not exist_command:
        raise TypeError(f"{command} is not found.")
    return Command(exist_command, parts)


async def execute_command(message) -> tp.Union[str, dict]:
    try:
        executable = parse_command(message)
    except (TypeError, ValueError) as traceback:
        return traceback
    coroutine_or_func, args = executable.command, executable.args

    if isinstance(coroutine_or_func, Function):
        if args:
            return coroutine_or_func.func_obj(args)
        return coroutine_or_func.func_obj()
    elif isinstance(coroutine_or_func, Coroutine):
        if not args:
            return "[-] Expected at least 1 argument, got 0"
        request = AsyncRequest(coroutine_or_func.generator(args))
        return await request.run()
    else:
        raise ValueError(f"Expected either Coroutine or Function, got {type(coroutine_or_func)} instead.")


class AsyncServer:
    default_buffer_size = 4096

    def __init__(self, *, ip, port):
        self.tasks = collections.deque()
        self.address = ip, port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.event_loop = asyncio.get_event_loop()
        self.__bind_server()

    def __bind_server(self):
        self.server_socket.bind(self.address)
        self.server_socket.listen()
        self.server_socket.setblocking(False)

    async def accept_connection(self):
        loop = asyncio.get_event_loop()
        while True:
            client, address = await loop.sock_accept(self.server_socket)
            print(f"[+] Established connection with {address}.")
            loop.create_task(self.read_from_client(client, address))

    async def read_from_client(self, client, address):
        loop = asyncio.get_event_loop()
        while True:
            message = await loop.sock_recv(client, self.default_buffer_size)
            message = str(await execute_command(message.decode()))
            print(f"> Message from {address}: {message}")
            if not message:
                break
            await loop.sock_sendall(client, (message + "\n").encode())


if __name__ == "__main__":
    server = AsyncServer(ip="192.168.196.199", port=9090)
    asyncio.run(server.accept_connection())




