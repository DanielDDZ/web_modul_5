import asyncio
import logging
import platform
import aiohttp
import names
import websockets

from aiofile import async_open
from aiopath import AsyncPath
from datetime import datetime

logging.basicConfig(level=logging.INFO)


class Server:
    clients = set()

    async def register(self, ws: websockets.WebSocketServerProtocol):
        ws.name = names.get_full_name()
        self.clients.add(ws)
        logging.info(f'{ws.remote_address} connects')

    async def unregister(self, ws: websockets.WebSocketServerProtocol):
        self.clients.remove(ws)
        logging.info(f'{ws.remote_address} disconnects')

    async def send_to_clients(self, message: str):
        if self.clients:
            [await client.send(message) for client in self.clients]

    async def ws_handler(self, ws: websockets.WebSocketServerProtocol):
        await self.register(ws)
        try:
            await self.distrubute(ws)
        except websockets.WebSocketProtocolError as err:
            logging.error(err)
        finally:
            await self.unregister(ws)

    async def distrubute(self, ws: websockets.WebSocketServerProtocol):
        async for message in ws:
            if message == 'exchange':
                message = await self.get_exchange()
                await self.save_to_file(message)
                await self.send_to_clients(message)
            else:
                await self.send_to_clients(f"{ws.name}: {message}")


    async def get_exchange(self):
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5') as resp:
                if resp.status == 200:
                    r = await resp.json()
                    exc, = list(filter(lambda el: el['ccy'] == 'USD', r))
                return f"USD: buy: {exc['buy']}, sale: {exc['sale']}"


    async def save_to_file(self, message):
        path = AsyncPath('exchange.txt')
        if await path.exists():
            async with async_open('exchange.txt', 'a') as af:
                await af.write(message + '\n')
        else:
            async with async_open('exchange.txt', 'w') as af:
                await af.write(message + '\n')


async def main():
    server = Server()
    async with websockets.serve(server.ws_handler, 'localhost', 8080):
        await asyncio.Future()  # run forever


if __name__ == '__main__':
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
