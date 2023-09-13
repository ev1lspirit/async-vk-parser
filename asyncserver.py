import dataclasses
from vk_parser import vk_parser
from service_functions import execute_command
from representation_functions import StaticResponse
import socket
import asyncio


@dataclasses.dataclass
class ClientAddress:
    ip: str
    port: int

    @property
    def tuple(self):
        return self.ip, self.port


class AsyncServer:
    default_buffer_size = 4096

    def __init__(self, *, address: ClientAddress):
        self.address = address
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.event_loop = asyncio.get_event_loop()
        self.__bind_server()

    @classmethod
    def bind(cls, *, ip: str, port: int):
        return cls(address=ClientAddress(ip=ip, port=port))

    def __bind_server(self):
        self.server_socket.bind(self.address.tuple)
        self.server_socket.listen()
        self.server_socket.setblocking(False)

    async def accept_connection(self):
        loop = asyncio.get_event_loop()
        while True:
            client, address = await loop.sock_accept(self.server_socket)
            print(f"[+] Established connection with {address}.")
            loop.create_task(self.read_from_client(client, address))

    async def read_from_client(self, client, address):
        ip, port = address
        loop = asyncio.get_event_loop()
        await loop.sock_sendall(client, (StaticResponse.greetings(ip_address=address)).encode())
        while True:
            try:
                message = await loop.sock_recv(client, self.default_buffer_size)
            except ConnectionResetError:
                print(f"[-] {ip}, port {port} disconnected.")
                break
            print(f"> Message from {ip}, port {port}: {message}")
            message = await execute_command(message.decode())
            value = vk_parser.FriendsParser(message)
            print(value.parse())
            message = str(message)
            if not message:
                break
            try:
                await loop.sock_sendall(client, (message + "\n").encode())
            except ConnectionAbortedError:
                print(f"[-] {ip}, port {port} disconnected.")
                break

        client.close()

    def listen(self):
        asyncio.run(self.accept_connection())






