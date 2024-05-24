from datetime import datetime, date

from aiogram import F, Router, types
from aiogram.filters import Command, StateFilter, or_f, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.chat_types import ChatTypeFilter, IsAdmin
from database.orm_query import orm_get_events, orm_add_online, orm_get_event, orm_get_online, orm_delete_online, \
    orm_get_online_for_change, orm_update_online
from handlers.keyboards import get_keyboard, get_keyboard_list
from handlers.keyboards_inline import get_callback_btns, get_url_btns

user_router = Router()
user_router.message.filter(ChatTypeFilter(["private"]))

USER_KB = get_keyboard("Мои результаты",
                       "Зарегистрировать результат",
                       placeholder="Выберите действие",
                       sizes=(1, 1),
                       )

DELIVERY_KB = get_keyboard("Заберу в магазине TOP LIGA RUN в Краснодаре",
                           "Отправить СДЭКом",
                           placeholder="Выберите действие",
                           sizes=(1, 1),
                           )


class AddResult(StatesGroup):
    # Шаги состояний
    event = State()
    distance = State()
    photo = State()
    participants_name = State()
    recipient_name = State()
    phone = State()
    delivery = State()
    city = State()
    address = State()
    code = State()

    product_for_change = None

    texts = {
        'AddProduct:distance': 'Введите дистанцию из списка:',
        'AddProduct:photo': 'Загрузите фото заново:',
        'AddProduct:participants_name': 'Введите ФИО участника заново:',
        'AddProduct:phone': 'Введите номер телефона заново:',
        'AddProduct:delivery': 'Введите тип доставки заново:',
        'AddProduct:recipient_name': 'Введите ФИО получателя заново:',
        'AddProduct:city': 'Введите город заново:',
        'AddProduct:address': 'Введите адрес заново:',
        'AddProduct:code': 'Введите код пункта выдачи заново:',
    }


@user_router.message(StateFilter(None), or_f(Command("start"), F.text == "Зарегистрировать результат"))
async def user_start(message: types.Message, state: FSMContext, session: AsyncSession):
    events = await orm_get_events(session)
    btns = {event.name: str(event.id) for event in events}
    # print(btns)
    await message.answer(f'Поздравляем вас с финишем Онлайн-забега! '
                         f'\nЗдесь вы можете загрузить свой результат, '
                         f'чтобы мы могли отправить вам стартовый пакет с заслуженной медалью '
                         f'\nПодготовьте скриншот трека вашего забега, а также адрес удобного офиса СДЭК.'
                         f'Если сделали ошибку при вводе данных введите "назад", чтобы вернуться на шаг назад.'
                         f'Чтобы отменить загрузку результата введите "отмена".')
    await message.answer(f"Выберите мероприятие", reply_markup=get_callback_btns(btns=btns))
    await state.set_state(AddResult.event)


@user_router.message(F.text == "Мои результаты")
async def starring_at_product(message: types.Message, session: AsyncSession):
    user = message.from_user
    result = await orm_get_online(session, user.id)
    for result in await orm_get_online(session, user.id):
        await message.answer_photo(
            result.photo,
            caption=f"Участник: {result.participants_name} "
                    f"\nПолучатель: {result.recipient_name}"
                    f"\nТелефон: {result.phone}"
                    f"\n Способ доставки: {result.delivery}"
                    f"\n Город: {result.city}"
                    f"\n Адрес: {result.address}"
                    f"\n Код выдачи: {result.code}",
            reply_markup=get_callback_btns(
                btns={
                    "Удалить": f"deleteresult_{result.id}",
                    "Изменить": f"changeresult_{result.id}",
                }
            ),
        )


@user_router.callback_query(F.data.startswith("deleteresult_"))
async def delete_online_callback(callback: types.CallbackQuery, session: AsyncSession):
    id_online = callback.data.split("_")[-1]
    await orm_delete_online(session, int(id_online))
    await callback.answer("Товар удален")
    await callback.message.answer("Товар удален!")


# Становимся в состояние ожидания ввода name
@user_router.callback_query(StateFilter(None), F.data.startswith("changeresult_"))
async def change_online_callback(
        callback: types.CallbackQuery, state: FSMContext, session: AsyncSession
):
    id_online = callback.data.split("_")[-1]
    product_for_change = await orm_get_online_for_change(session, int(id_online))

    AddResult.product_for_change = product_for_change

    events = await orm_get_events(session)
    btns = {event.name: str(event.id) for event in events}
    await callback.answer()
    await callback.message.answer(f"Для того чтобы оставить пункт без изменения введите .")
    await callback.message.answer("Выберите мероприятие", reply_markup=get_callback_btns(btns=btns))
    await state.set_state(AddResult.event)


@user_router.message(StateFilter('*'), Command("отмена"))
@user_router.message(StateFilter('*'), F.text.casefold() == "отмена")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    if AddResult.product_for_change:
        AddResult.product_for_change = None
    await state.clear()
    await message.answer("Действия отменены", reply_markup=USER_KB)


# Вернутся на шаг назад (на прошлое состояние)
@user_router.message(StateFilter('*'), Command("назад"))
@user_router.message(StateFilter('*'), F.text.casefold() == "назад")
async def back_step_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()

    if current_state == AddResult.recipient_name:
        await message.answer('Предыдущего шага нет, напишите "отмена"')
        return

    previous = None
    for step in AddResult.__all_states__:
        if step.state == current_state:
            await state.set_state(previous)
            await message.answer(f"Ок, вы вернулись к прошлому шагу \n {AddResult.texts[previous.state]}")
            return
        previous = step


@user_router.callback_query(AddResult.event)
async def add_event(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    events = await orm_get_events(session)
    # ты пытаешься строку 'changeresult_3' привести к типу целочисленного значения
    print(callback)
    if int(callback.data) in [event.id for event in events]:
        await callback.answer()
        # await state.update_data(event=event.name)
        event = await orm_get_event(session, int(callback.data))
        await state.update_data(event=callback.data)
        btns = event.distance
        DISTANCE_KB = get_keyboard_list(btns,
                                        placeholder="Выберите действие",
                                        sizes=(1, 2, 2),
                                        )

        await callback.message.answer(f"Поздравляем с финишем онлайн забега {event.name}!\n"
                                      f"Какую дистанцию вы преодолели?", reply_markup=DISTANCE_KB)
        await state.set_state(AddResult.distance)
    else:
        await callback.message.answer('Выберите мероприятие из кнопок.')
        await callback.answer()


@user_router.message(AddResult.distance, or_f(F.text, F.text == "."))
async def add_distance(message: types.Message, state: FSMContext):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(distence=AddResult.product_for_change.distance)
    else:
        await state.update_data(distance=message.text)
    await message.answer("Отправьте скриншот/фото с подтверждением результата (загрузите только 1 изображение)")
    await state.set_state(AddResult.photo)


@user_router.message(AddResult.distance)
async def add_distance2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите дистанцию заново")


@user_router.message(AddResult.photo, or_f(F.photo, F.text == "."))
async def add_photo(message: types.Message, state: FSMContext):
    if message.text and message.text == "." and AddResult.product_for_change:
        await state.update_data(photo=AddResult.product_for_change.photo)
    else:
        await state.update_data(photo=message.photo[-1].file_id)
    await message.answer("Введите ФИО участника")
    await state.set_state(AddResult.participants_name)


@user_router.message(AddResult.photo)
async def add_photo2(message: types.Message, state: FSMContext):
    await message.answer("Отправьте скриншот забега")


@user_router.message(AddResult.participants_name, or_f(F.text, F.text == "."))
async def add_participants_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(participants_name=AddResult.product_for_change.participants_name)
    else:
        await state.update_data(participants_name=message.text)
    await message.answer("Введите номер телефона в формате 7хххххххххх (без '+')")
    await state.set_state(AddResult.phone)


@user_router.message(AddResult.participants_name)
async def add_participants_name2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите ФИО заново")


@user_router.message(AddResult.phone, or_f(F.text, F.text == "."))
async def add_phone(message: types.Message, state: FSMContext):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(phone=AddResult.product_for_change.phone)
    else:
        try:
            int(message.text)
            if len(message.text) != 11:
                raise Exception('incorrect phone number length')
        except ValueError:
            await message.answer("Введите номер телефона без дополнительных символов")
            return
        except Exception:
            await message.answer("Некорректная длина номер телефона, введите номер телефона еще раз")
            return
    await state.update_data(phone=message.text)

    await message.answer("Как вам удобно будет забрать стартовый пакет", reply_markup=DELIVERY_KB)
    await state.set_state(AddResult.delivery)


@user_router.message(AddResult.phone)
async def add_phone2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите номер телефона заново")


@user_router.message(AddResult.delivery, or_f(F.text, F.text == "."))
async def add_delivery(message: types.Message, state: FSMContext, session: AsyncSession):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(delivery=AddResult.product_for_change.delivery)
    elif message.text == "Отправить СДЭКом":
        await state.update_data(delivery=message.text)
        await message.answer("Укажите ФИО получателя стартового пакета")
        await state.set_state(AddResult.recipient_name)
    else:
        user = message.from_user
        await state.update_data(delivery=message.text)
        await state.update_data(recipient_name='Забрать пакет можно по фамилии участника')
        await state.update_data(city='Краснодар')
        await state.update_data(address='ул. Кубанская Набережная 1/о')
        await state.update_data(code='')
        await state.update_data(id_user=user.id)
        data = await state.get_data()

        event = await orm_get_event(session, int(data['event']))
        await message.answer(f"Забрать стартовый пакет можно после {event.pick_up_data.strftime("%d.%m")} "
                             f"в магазине TOP LIGA RUN на Кубанской набережной 1/о", reply_markup=USER_KB)
        # await message.answer(str(data))
        try:

            if AddResult.product_for_change:
                await orm_update_online(session, AddResult.product_for_change.id, data)
                await message.answer("Результат изменен", reply_markup=USER_KB)
            else:
                await orm_add_online(session, data)
                await message.answer("Результат добавлен", reply_markup=USER_KB)
                await message.answer(f'Посмотреть, изменить или удалить результат можно нажав \b"Мои результаты"\b'
                                     f'\nНажмите \b"загрузить результат"\b, если хотите загрузить результат за другого участника',
                                     reply_markup=USER_KB)
            await state.clear()

        except Exception as e:
            await message.answer(
                f"Ошибка: \n{str(e)}\n. Попробуйте снова.",
                reply_markup=USER_KB,
            )
            await state.clear()
        await state.clear()
        AddResult.product_for_change = None


@user_router.message(AddResult.delivery)
async def add_delivery2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, выбирете один из вариантов на клавиатуре")

@user_router.message(AddResult.recipient_name, or_f(F.text, F.text == "."))
async def add_recipient_name(message: types.Message, state: FSMContext):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(recipient_name=AddResult.product_for_change.recipient_name)
    else:

        await state.update_data(recipient_name=message.text)
    await message.answer("Укажите город доставки")
    await state.set_state(AddResult.city)


@user_router.message(AddResult.recipient_name)
async def add_recipient_name2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите ФИО заново")


@user_router.message(AddResult.city, or_f(F.text, F.text == "."))
async def add_city(message: types.Message, state: FSMContext):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(city=AddResult.product_for_change.city)
    else:
        await state.update_data(city=message.text)
    sdek = {'Узнать пункт выдачи': 'https://www.cdek.ru/ru/offices/'}
    await message.answer(f"Доставка возможна только до пункта выдачи СДЭК. \n"
                         f"Узнать адрес выдачи можнно нпо ссылке: https://www.cdek.ru/ru/offices/\n"
                         f"Укажите адрес удобного офиса СДЭК",
                         reply_markup=get_url_btns(btns={'Узнать пункт выдачи': 'https://www.cdek.ru/ru/offices/'}))
    await state.set_state(AddResult.address)


@user_router.message(AddResult.city)
async def add_city2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите город заново")


@user_router.message(AddResult.address, or_f(F.text, F.text == "."))
async def add_address(message: types.Message, state: FSMContext):
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(address=AddResult.product_for_change.address)
    else:
        await state.update_data(address=message.text)
    await message.answer(f"Укажите код пункта выдачи СДЭК")
    await state.set_state(AddResult.code)


@user_router.message(AddResult.address)
async def add_address2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, ведите адрес удобного офиса СДЭК")


@user_router.message(AddResult.code, or_f(F.text, F.text == "."))
async def add_code(message: types.Message, state: FSMContext, session: AsyncSession):
    user = message.from_user
    if message.text == "." and AddResult.product_for_change:
        await state.update_data(code=AddResult.product_for_change.code)
    else:
        await state.update_data(code=message.text)
        await state.update_data(id_user=user.id)
    data = await state.get_data()
    event = await orm_get_event(session, int(data['event']))
    await message.answer(f"Пакеты будут отправлены после {event.data_finish.strftime("%d.%m")}. "
                         f"Вам придет смс на указаный ранее номер телефона")
    try:

        if AddResult.product_for_change:
            await orm_update_online(session, AddResult.product_for_change.id, data)
            await message.answer("Результат изменен", reply_markup=USER_KB)
        else:
            await orm_add_online(session, data)
            await message.answer("Результат добавлен", reply_markup=USER_KB)
            await message.answer(f'Посмотреть, изменить или удалить результат можно нажав \b"Мои результаты"\b'
                                 f'\nНажмите \b"загрузить результат"\b, если хотите загрузить результат за другого участника',
                                 reply_markup=USER_KB)
        await state.clear()


    except Exception as e:
        await message.answer(
            f"Ошибка: \n{str(e)}\n. Попробуйте снова.",
            reply_markup=USER_KB,
        )
        await state.clear()
    await state.clear()
    AddResult.product_for_change = None


@user_router.message(AddResult.code)
async def add_code2(message: types.Message, state: FSMContext):
    await message.answer("Вы ввели не допустимые данные, введите код выдачи СДЭК")
