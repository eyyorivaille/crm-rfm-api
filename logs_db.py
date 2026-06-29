import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

load_dotenv()

LOGS_DATABASE_URL = (
    f"postgresql+asyncpg://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('LOGS_DB_NAME')}"
)

logs_engine = create_async_engine(LOGS_DATABASE_URL)
LogsSessionLocal = async_sessionmaker(logs_engine, expire_on_commit=False)


async def get_logs_db():
    async with LogsSessionLocal() as session:
        yield session
