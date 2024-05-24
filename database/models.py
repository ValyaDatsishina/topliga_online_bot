from sqlalchemy import String, DateTime, func, ARRAY, Date, BigInteger
from sqlalchemy.orm import declarative_base, Mapped, mapped_column

Base = declarative_base()
class Event(Base):
    __tablename__ = 'event'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    data_start: Mapped[DateTime] = mapped_column(DateTime)
    data_finish: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    pick_up_data: Mapped[Date] = mapped_column(Date, nullable=False)
    distance: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)

class Online(Base):
    __tablename__ = 'online'
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    id_user: Mapped[int] = mapped_column(BigInteger)
    distance: Mapped[str] = mapped_column(String(400), nullable=False)
    photo: Mapped[str] = mapped_column(String(150))
    participants_name: Mapped[str] = mapped_column(String(400), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(400), nullable=False)
    phone: Mapped[str] = mapped_column(String(11), nullable=False)
    delivery: Mapped[str] = mapped_column(String(400), nullable=False)
    city: Mapped[str] = mapped_column(String(400), nullable=True)
    address: Mapped[str] = mapped_column(String(500), nullable=True)
    code: Mapped[str] = mapped_column(String(10), nullable=True)
    data: Mapped[DateTime] = mapped_column(DateTime, default=func.now())

