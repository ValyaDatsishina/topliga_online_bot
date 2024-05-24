from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from database.models import Event, Online


async def orm_add_event(session: AsyncSession, data: dict):
    obj = Event(
        name=data['name'],
        data_start=data['data_start'],
        data_finish=data['data_finish'],
        pick_up_data=data['pick_up_data'],
        distance=data['distance']
    )
    session.add(obj)
    await session.commit()


async def orm_get_events(session: AsyncSession):
    query = select(Event)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_event(session: AsyncSession, product_id: int):
    query = select(Event).where(Event.id == product_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_event(session: AsyncSession, product_id: int, data):
    query = update(Event).where(Event.id == product_id).values(
        name=data['name'],
        data_start=data['data_start'],
        data_finish=data['data_finish'],
        pick_up_data=data['pick_up_data'],
        distance=data['distance']
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_event(session: AsyncSession, product_id: int):
    query = delete(Event).where(Event.id == product_id)
    await session.execute(query)
    await session.commit()


async def orm_add_online(session: AsyncSession, data: dict):
    obj = Online(
        id_user=data['id_user'],
        distance=data['distance'],
        photo=data['photo'],
        participants_name=data['participants_name'],
        recipient_name=data['recipient_name'],
        phone=data['phone'],
        delivery=data['delivery'],
        city=data['city'],
        address=data['address'],
        code=data['code']
    )
    session.add(obj)
    await session.commit()

async def orm_get_online_all(session: AsyncSession):
    query = select(Online)
    result = await session.execute(query)

    return result.scalars().all()

async def orm_get_online(session: AsyncSession, id_user: int):
    query = select(Online).where(Online.id_user == id_user)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_online_for_change(session: AsyncSession, id_online: int):
    query = select(Online).where(Online.id == id_online)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_online(session: AsyncSession, id_user: int, data):
    query = update(Online).where(Online.id == id_user).values(
        id_user=data['id_user'],
        distance=data['distance'],
        photo=data['photo'],
        participants_name=data['participants_name'],
        recipient_name=data['recipient_name'],
        phone=data['phone'],
        delivery=data['delivery'],
        city=data['city'],
        address=data['address'],
        code=data['code']
    )
    await session.execute(query)
    await session.commit()


async def orm_delete_online(session: AsyncSession, id_online: int):
    query = delete(Online).where(Online.id == id_online)
    await session.execute(query)
    await session.commit()
