from datetime import datetime, date
import pandas as pd
import pandas.io.sql as psql

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine
from database.engine import connection
from handlers.chat_types import ChatTypeFilter, IsAdmin
from database.orm_query import orm_add_event, orm_get_events, orm_delete_event, orm_get_event, orm_update_event
from handlers.keyboards import get_keyboard
from handlers.keyboards_inline import get_callback_btns

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

ADMIN_KB = get_keyboard(
    "Добавить мероприятие",
    "Все старты",
    "Все результаты",
    "Выгрузить результаты",
    placeholder="Выберите действие",
    sizes=(2,),
)


# Код ниже для машины состояний (FSM)

class AddProduct(StatesGroup):
    # Шаги состояний
    name = State()
    data_start = State()
    data_finish = State()
    pick_up_data = State()
    distance = State()

    product_for_change = None

    texts = {
        'AddProduct:name': 'Введите название заново:',
        'AddProduct:data_start': 'Введите начальную дату заново:',
        'AddProduct:data_finish': 'Введите конечную дату заново:',
        'AddProduct:pick_up_data': 'Введите конечную дату заново:',
        'AddProduct:distance': 'Введите дистанции через , и пробел',
    }


@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)


@admin_router.message(F.text == "Все старты")
async def starring_at_product(message: types.Message, session: AsyncSession):
    for event in await orm_get_events(session):
        await message.answer(f"{event.name}\
                        \n{event.distance}\nДаты: {event.data_start} - {event.data_finish}",
                             reply_markup=get_callback_btns(
                                 btns={
                                     "Удалить": f"delete_{event.id}",
                                     "Изменить": f"change_{event.id}",
                                 }
                             ),
                             )


@admin_router.callback_query(F.data.startswith("delete_"))
async def delete_product_callback(callback: types.CallbackQuery, session: AsyncSession):
    event_id = callback.data.split("_")[-1]
    await orm_delete_event(session, int(event_id))

    await callback.answer("Товар удален")
    await callback.message.answer("Товар удален!")


# Становимся в состояние ожидания ввода name
@admin_router.callback_query(StateFilter(None), F.data.startswith("change_"))
async def change_product_callback(
        callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    event_id = callback.data.split("_")[-1]

    product_for_change = await orm_get_event(session, int(event_id))

    AddProduct.product_for_change = product_for_change

    await callback.answer()
    await callback.message.answer(
        "Введите название старта", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


@admin_router.message(StateFilter(None), F.text == "Добавить мероприятие")
async def add_product(message: types.Message, state: FSMContext):
    await message.answer(
        "Введите название старта", reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(AddProduct.name)


@admin_router.message(StateFilter(None), F.text == "Выгрузить результаты")
async def add_product(message: types.Message, state: FSMContext, session: AsyncSession):
    # online = await orm_get_events(session)
    table_df = pd.read_sql_table(
        "Online",
        con=engine,
        columns=['distance',
                 'photo',
                 'participants_name'],

    )
    print(table_df)




# Хендлер отмены и сброса состояния должен быть всегда именно хдесь,
# после того как только встали в состояние номер 1 (элементарная очередность фильтров)
@admin_router.message(StateFilter('*'), Command("отмена"))
@admin_router.message(StateFilter('*'), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddProduct.product_for_change:
        AddProduct.product_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=ADMIN_KB)


# Вернутся на шаг назад (на прошлое состояние)
@admin_router.message(StateFilter('*'), Command("назад"))
@admin_router.message(StateFilter('*'), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddProduct.name:
        await message.answer('Предыдущего шага нет, или введите название товара или напишите "отмена"')
        return

    previous = None
    for step in AddProduct.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Ок, вы вернулись к прошлому шагу \n {AddProduct.texts[previous.state]}")
            return
        previous = step


# Ловим данные для состояние name и потом меняем состояние на data_start
@admin_router.message(AddProduct.name, or_f(F.text, F.text == "."))
async def add_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(name=AddProduct.product_for_change.name)
    else:
        # Здесь можно сделать какую либо дополнительную проверку
        # и выйти из хендлера не меняя состояние с отправкой соответствующего сообщения
        # например:
        if len(message.text) >= 100:
            await message.answer("Название старта не должно превышать 100 символов. \n Введите заново")
            return

        await state.update_data(name=message.text)
    await message.answer("Введите начальную дату приема результатов")
    await state.set_state(AddProduct.data_start)


# Хендлер для отлова некорректных вводов для состояния name
@admin_router.message(AddProduct.name)
async def add_name2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите название старта заново")


# Ловим данные для состояние data_start и потом меняем состояние на data_finish
@admin_router.message(AddProduct.data_start, or_f(F.text, F.text == "."))
async def add_data_start(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(data_start=AddProduct.product_for_change.data_start)
    else:
        try:
            datetime.strptime(message.text, '%d.%m.%Y').date()
        except ValueError:
            await message.answer("Введите корректную дату, формат 20.03.2024")
            return

        await state.update_data(data_start=datetime.strptime(message.text, '%d.%m.%Y').date())
    await message.answer("Введите конечную дату приема результатов")
    await state.set_state(AddProduct.data_finish)


# Хендлер для отлова некорректных вводов для состояния data_start
@admin_router.message(AddProduct.data_start)
async def add_data_start2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите начальную дату приема результатов")


# Ловим данные для состояния data_finish и потом меняем состояние на distance
@admin_router.message(AddProduct.data_finish, or_f(F.text, F.text == "."))
async def add_data_finish(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(data_finish=AddProduct.product_for_change.data_finish)
    else:
        try:
            datetime.strptime(message.text, '%d.%m.%Y').date()
        except ValueError:
            await message.answer("Введите корректную дату, формат 20.03.2024")
            return

        await state.update_data(data_finish=datetime.strptime(message.text, '%d.%m.%Y').date())
    await message.answer("Введите дату после которой можно забрать в магазине")
    await state.set_state(AddProduct.pick_up_data)


# Хендлер для отлова некорректных ввода для состояния data_finish
@admin_router.message(AddProduct.data_finish)
async def add_data_finish2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите дату заново")


@admin_router.message(AddProduct.pick_up_data, or_f(F.text, F.text == "."))
async def add_pick_up_data(message: types.Message, state: FSMContext):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(pick_up_data=AddProduct.product_for_change.data_finish)
    else:
        try:
            datetime.strptime(message.text, '%d.%m.%Y').date()
        except ValueError:
            await message.answer("Введите корректную дату, формат 20.03.2024")
            return

        await state.update_data(pick_up_data=datetime.strptime(message.text, '%d.%m.%Y').date())
    await message.answer("Введите дистанции через , и пробел")
    await state.set_state(AddProduct.distance)


# Хендлер для отлова некорректных ввода для состояния data_finish
@admin_router.message(AddProduct.pick_up_data)
async def add_pick_up_data2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите дату заново")


# Ловим данные для состояние distance и потом выходим из состояний
@admin_router.message(AddProduct.distance, or_f(F.text, F.text == "."))
async def add_distance(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == "." and AddProduct.product_for_change:
        await state.update_data(distance=AddProduct.product_for_change.distance)
    else:

        await state.update_data(distance=message.text.split(', '))
    data = await state.get_data()
    await message.answer(str(data))
    try:

        if AddProduct.product_for_change:
            await orm_update_event(session, AddProduct.product_for_change.id, data)
        else:
            await orm_add_event(session, data)
        await message.answer("Мероприятие добавлено", reply_markup=ADMIN_KB)
        await state.clear()

    except Exception as e:
        await message.answer(
            f"Ошибка: \n{str(e)}\n. Попробуйте снова.",
            reply_markup=ADMIN_KB,
        )
        await state.clear()
    await state.clear()
    AddProduct.product_for_change = None

# @admin_router.message(AddProduct.distance)
# async def add_distance2(message: types.Message, state: FSMContext):
#     await message.answer("Отправьте фото пищи")
