import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart

import os
from dotenv import load_dotenv, find_dotenv, dotenv_values

from handlers.user_private import user_router

load_dotenv(find_dotenv())

from middlewares.db import DataBaseSession

from database.engine import create_db, drop_db, session_maker

from handlers.admin_private import admin_router
from handlers.user_private import user_router


logging.basicConfig(level=logging.INFO)

ALLOWED_UPDATES = ['message, edited_message']
# api_token = os.getenv('TELEGRAM_API_TOKEN')
# print(api_token)
config = dotenv_values('.env')
api_token = config['TELEGRAM_API_TOKEN']

token = os.getenv('TOKEN')
# print(token)
bot = Bot(token=api_token)

bot.my_admins_list = []
for i in range(0, 5):
    bot.my_admins_list.append(int(os.getenv(f'USER_ID_{i}')))

dp = Dispatcher(bot=bot)
# print(bot)
# print(dp)

dp.include_router(admin_router)
dp.include_router(user_router)


async def on_startup(bot):
    run_param = False
    if run_param:
        await drop_db()

    await create_db()


# async def on_shutdown(bot):
#     print('бот лег')


async def main():
    dp.startup.register(on_startup)
    # dp.shutdown.register(on_shutdown)

    dp.update.middleware(DataBaseSession(session_pool=session_maker))

    await bot.delete_webhook(drop_pending_updates=True)
    # await bot.delete_my_commands(scope=types.BotCommandScopeAllPrivateChats())
    # await bot.set_my_commands(commands=private, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


asyncio.run(main())
