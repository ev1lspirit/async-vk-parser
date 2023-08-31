
class StaticResponse:

    @staticmethod
    def greetings(ip_address):
        return f"Hi, {ip_address}. This is simple asynchronous server. Type 'help' to know what this server can do."

    @staticmethod
    def help(*args, **kwargs):
        return f"\n---------------------------------\n~ 'echo' -\t command enables echo mode: server sends back your message" \
               f'\n~ "friends <VK id or username>" -\t returns a list of VK friends of a particular id' \
               f"\n~ 'ismutual <id1> <id2>' -\t returns a list of mutual friends between two users\n"