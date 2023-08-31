from asyncserver import AsyncServer

if __name__ == "__main__":
    server = AsyncServer.bind(ip="localhost", port=9090)
    server.listen()



