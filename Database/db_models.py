from sqlalchemy import String, ForeignKey, Boolean, create_engine
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
import uuid
import os

from sqlalchemy_utils import create_database, database_exists


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:secret@localhost:5432/swift_db")
engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def validate_database():
    if not database_exists(engine.url):
        create_database(engine.url)


class Base(DeclarativeBase):
    pass



class SwiftData(Base):
    __tablename__ = 'swift_data'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    bank_name: Mapped[str] = mapped_column(String(200), nullable = False)
    country_iso2: Mapped[str] = mapped_column(String(2), nullable= False)
    country_name: Mapped[str] = mapped_column(String(200), nullable= False)
    swift_code: Mapped[str] = mapped_column(String(11), nullable=False, unique=True)
    address: Mapped[str] = mapped_column(String(200), nullable = True)

    is_headquarter: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    headquarter_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True),
                                                             ForeignKey("swift_data.id",ondelete="SET NULL"), nullable=True)


    headquarter: Mapped["SwiftData"] = relationship(
        back_populates="branches", remote_side="SwiftData.id"
    )

    branches: Mapped[list["SwiftData"]] = relationship(
        back_populates="headquarter", cascade="save-update, merge, refresh-expire"
    )

    def __repr__(self):
        return f"<SwiftData {self.swift_code} ({'HQ' if self.is_headquarter else 'Branch'})>"


