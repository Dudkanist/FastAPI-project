from sqlalchemy import create_url, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Путь к локальной базе данных
SQLALCHEMY_DATABASE_URL = "sqlite:///./gene_vault.db"

# Создаем движок для подключения к базе
# check_same_thread=False нужен для SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Создаем фабрику сессий, чтобы общаться с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс для наших будущих моделей (таблиц)
Base = declarative_base()

# Зависимость для эндпоинтов
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
