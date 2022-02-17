import asyncio
import time
from queue import Queue
from threading import Thread
from aiogram import Bot, types
from aiogram.types.message import ContentType
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import Dispatcher, FSMContext
from aiogram.utils.executor import start_webhook
from utilities.config import (BOT_TOKEN, WEBHOOK_URL, WEBHOOK_PATH,
                              WEBAPP_HOST, WEBAPP_PORT)
from utilities.messages import (START_MESSAGE, HELP_MESSAGE, NST_MESSAGE, GAN_MESSAGE,
                                CANCEL_MESSAGE, CHOOSE_STYLE_ERROR_MESSAGE,
                                WAITING_FOR_CONTENT_MESSAGE, WAITING_FOR_CONTENT_GAN_MESSAGE,
                                GETTING_CONTENT_ERROR_MESSAGE, GETTING_STYLE_ERROR_MESSAGE,
                                PROCESSING_MESSAGE, CONFUSED_MESSAGE, FINISHED_MESSAGE)
from utilities.keyboard import START_KB, GAN_KB
from utilities.states import NST_States, GAN_States
from models.NST import nst
from models.GAN import gan
import logging

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())
dp.middleware.setup(LoggingMiddleware())

task_queue = Queue()


@dp.message_handler(commands=["start"])
async def start_command(message: types.Message):
    await message.answer(START_MESSAGE,
                         reply_markup=START_KB)


@dp.message_handler(commands=["help"], state="*")
async def help_command(message: types.Message):
    await message.answer(HELP_MESSAGE,
                         reply_markup=START_KB)


@dp.message_handler(commands=["nst"])
async def choose_nst_command(message: types.Message):
    await NST_States.waiting_for_style.set()
    await message.answer(NST_MESSAGE)


@dp.message_handler(commands=["gan"])
async def choose_gan_command(message: types.message):
    await GAN_States.waiting_for_style.set()
    await message.answer(GAN_MESSAGE,
                         reply_markup=GAN_KB)


@dp.message_handler(commands=["cancel"], state="*")
async def cancel_action_command(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.finish()
    await message.answer(CANCEL_MESSAGE)


@dp.message_handler(state=NST_States.waiting_for_style, content_types=ContentType.ANY)
async def handle_style_input_nst(message: types.message, state: FSMContext):
    if len(message.photo) > 0:
        await state.update_data(style=message.photo[-1])
        await NST_States.waiting_for_content.set()
        await message.answer(WAITING_FOR_CONTENT_MESSAGE)
    else:
        await message.answer(GETTING_STYLE_ERROR_MESSAGE)


@dp.message_handler(state=NST_States.waiting_for_content, content_types=ContentType.ANY)
async def handle_content_input_nst(message: types.message, state: FSMContext):
    if len(message.photo) > 0:
        await message.answer(PROCESSING_MESSAGE)
        data = await state.get_data()
        content = message.photo[-1]
        style = data["style"]

        style_path = f"images/{style.file_id}.jpg"
        content_path = f"images/{content.file_id}.jpg"

        await style.download(style_path)
        await content.download(content_path)

        task = {"id": message.chat.id, "type": "nst",
                "style": style_path, "content": content_path,
                "loop": asyncio.get_event_loop()}
        task_queue.put(task)

        await state.finish()
    else:
        await message.answer(GETTING_CONTENT_ERROR_MESSAGE)


@dp.callback_query_handler(lambda c: c.data == "cezanne", state=GAN_States.waiting_for_style)
async def process_callback_cezanne(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await GAN_States.waiting_for_content.set()
    await bot.send_message(callback_query.from_user.id, WAITING_FOR_CONTENT_GAN_MESSAGE)
    await state.update_data(model="style_cezanne")


@dp.callback_query_handler(lambda c: c.data == "monet", state=GAN_States.waiting_for_style)
async def process_callback_monet(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await GAN_States.waiting_for_content.set()
    await bot.send_message(callback_query.from_user.id, WAITING_FOR_CONTENT_GAN_MESSAGE)
    await state.update_data(model="style_monet")


@dp.callback_query_handler(lambda c: c.data == "vangogh", state=GAN_States.waiting_for_style)
async def process_callback_vangogh(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await GAN_States.waiting_for_content.set()
    await bot.send_message(callback_query.from_user.id, WAITING_FOR_CONTENT_GAN_MESSAGE)
    await state.update_data(model="style_vangogh")


@dp.message_handler(state=GAN_States.waiting_for_style, content_types=ContentType.ANY)
async def waiting_for_style(message: types.message):
    await message.answer(CHOOSE_STYLE_ERROR_MESSAGE)


@dp.message_handler(state=GAN_States.waiting_for_content, content_types=ContentType.ANY)
async def incoming_content_gan(message: types.message, state: FSMContext):
    if len(message.photo) > 0:
        await message.answer(PROCESSING_MESSAGE)
        data = await state.get_data()
        content = message.photo[-1]

        content_path = f"images/{content.file_id}.jpg"

        await content.download(content_path)

        task = {"id": message.chat.id, "type": "gan",
                "model": data["model"], "content": content.file_id,
                "loop": asyncio.get_event_loop()}
        task_queue.put(task)

        await state.finish()
    else:
        await message.answer(GETTING_CONTENT_ERROR_MESSAGE)


@dp.message_handler(content_types=ContentType.ANY)
async def wrong_input(message: types.Message):
    await message.answer(CONFUSED_MESSAGE,
                         reply_markup=START_KB)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)


async def on_shutdown(dp):
    pass


async def send_result(chat_id):
    await bot.send_photo(chat_id, open("images/result/res.jpg", "rb"), FINISHED_MESSAGE)


def queue_loop():
    while True:
        if not task_queue.empty():
            task = task_queue.get()
            if task["type"] == "nst":
                nst.run(task["style"], task["content"])
            else:
                gan.run(task["model"], task["content"])
            asyncio.run_coroutine_threadsafe(send_result(task["id"]), task["loop"]).result()
            task_queue.task_done()
        time.sleep(2)


if __name__ == "__main__":
    image_processing_thread = Thread(target=queue_loop, args=())
    image_processing_thread.start()

    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        skip_updates=False,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
