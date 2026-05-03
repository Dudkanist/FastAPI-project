from typing import Annotated, List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import auth, bio_calc, db, models, schemas

# Создаем таблицы в БД
models.Base.metadata.create_all(bind=db.engine)

app = FastAPI(title="GeneVault API")

# --- Настройка безопасности и зависимостей ---
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Псевдонимы типов для чистоты сигнатур функций
DbSession = Annotated[Session, Depends(db.get_db)]
TokenData = Annotated[str, Depends(oauth2_scheme)]


def get_current_user(token: TokenData, database: DbSession) -> models.User:
    """
    Извлекает и проверяет текущего пользователя из JWT-токена.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except auth.JWTError:
        raise credentials_exception

    user = database.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


# Зависимость для получения текущего пользователя
CurrentUser = Annotated[models.User, Depends(get_current_user)]


# --- Эндпоинты ---


@app.get("/", tags=["Healthcheck"])
async def root():
    return {"status": "alive", "database": "connected"}


@app.post("/register", response_model=schemas.UserResponse, tags=["Auth"])
def register_user(user: schemas.UserCreate, database: DbSession):
    """
    Создает нового пользователя, хеширует пароль и сохраняет его в БД.
    """
    db_user = (
        database.query(models.User).filter(models.User.email == user.email).first()
    )
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    hashed_pass = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pass)

    database.add(new_user)
    database.commit()
    database.refresh(new_user)

    return new_user


@app.post("/token", tags=["Auth"])
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    database: DbSession,
):
    """
    Принимает логин/пароль, проверяет их и выдает временный JWT-токен.
    """
    user = (
        database.query(models.User)
        .filter(models.User.email == form_data.username)
        .first()
    )

    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/sequences/", response_model=schemas.SequenceResponse, tags=["Sequences"])
def create_sequence(
    sequence: schemas.SequenceCreate,
    current_user: CurrentUser,
    database: DbSession,
):
    """
    Сохраняет ДНК-последовательность и автоматически запускает анализ.
    """
    # 1. Формируем запись последовательности
    db_sequence = models.Sequence(
        name=sequence.name,
        description=sequence.description,
        raw_sequence=bio_calc.clean_sequence(sequence.raw_sequence),
        molecule_type=sequence.molecule_type,
        owner_id=current_user.id,
    )
    database.add(db_sequence)

    # flush() отправляет запрос в БД и получает ID, но не фиксирует транзакцию
    database.flush()

    # 2. Считаем параметры
    gc = bio_calc.calculate_gc_content(db_sequence.raw_sequence)
    tm = bio_calc.calculate_melting_temp(db_sequence.raw_sequence)
    mw = bio_calc.calculate_molecular_weight(db_sequence.raw_sequence)

    # 3. Сохраняем результаты анализа
    db_analysis = models.AnalysisResult(
        sequence_id=db_sequence.id, gc_content=gc, melting_temp=tm, molecular_weight=mw
    )
    database.add(db_analysis)

    # Делаем один commit на обе операции (атомарность транзакции)
    database.commit()
    database.refresh(db_sequence)

    return db_sequence


@app.get(
    "/sequences/", response_model=List[schemas.SequenceResponse], tags=["Sequences"]
)
def read_sequences(
    current_user: CurrentUser,
    database: DbSession,
    skip: int = 0,
    limit: int = 100,
):
    """
    Возвращает список последовательностей текущего пользователя.
    """
    return (
        database.query(models.Sequence)
        .filter(models.Sequence.owner_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/sequences/{sequence_id}",
    response_model=schemas.SequenceResponse,
    tags=["Sequences"],
)
def read_sequence(
    sequence_id: int,
    current_user: CurrentUser,
    database: DbSession,
):
    """
    Получение детальной информации о конкретной записи и результатах её анализа.
    """
    sequence = (
        database.query(models.Sequence)
        .filter(
            models.Sequence.id == sequence_id,
            models.Sequence.owner_id == current_user.id,
        )
        .first()
    )

    if sequence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    return sequence


@app.delete(
    "/sequences/{sequence_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Sequences"],
)
def delete_sequence(
    sequence_id: int,
    current_user: CurrentUser,
    database: DbSession,
):
    """
    Удаление данных из системы.
    """
    sequence = (
        database.query(models.Sequence)
        .filter(
            models.Sequence.id == sequence_id,
            models.Sequence.owner_id == current_user.id,
        )
        .first()
    )

    if sequence is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Sequence not found"
        )

    # Удаляем зависимости, если каскадное удаление не настроено на уровне ORM
    if sequence.analysis:
        database.delete(sequence.analysis)

    database.delete(sequence)
    database.commit()

    # 204 статус обязывает не возвращать тело ответа
    return None
