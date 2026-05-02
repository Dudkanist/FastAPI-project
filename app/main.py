from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from . import models, schemas, auth, db, bio_calc

# Создаем таблицы в БД
models.Base.metadata.create_all(bind=db.engine)

app = FastAPI(title="GeneVault API")

@app.post("/register", response_model=schemas.UserResponse, tags=["Auth"])
def register_user(user: schemas.UserCreate, database: Session = Depends(db.get_db)):
    # Проверяем, нет ли такого пользователя
    db_user = database.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Хешируем пароль и сохраняем
    hashed_pass = auth.get_password_hash(user.password)
    new_user = models.User(email=user.email, hashed_password=hashed_pass)
    database.add(new_user)
    database.commit()
    database.refresh(new_user)
    return new_user

@app.post("/token", tags=["Auth"])
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    database: Session = Depends(db.get_db)
):
    # Ищем пользователя по email (в OAuth2 поле называется username)
    user = database.query(models.User).filter(models.User.email == form_data.username).first()
    
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_01_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создаем токен
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/", tags=["Healthcheck"])
async def root():
    return {"status": "alive", "database": "connected"}

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_current_user(token: str = Depends(oauth2_scheme), database: Session = Depends(db.get_db)):
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    except auth.JWTError:
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    user = database.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.post("/sequences/", response_model=schemas.SequenceResponse, tags=["Sequences"])
def create_sequence(
    sequence: schemas.SequenceCreate, 
    current_user: models.User = Depends(get_current_user),
    database: Session = Depends(db.get_db)
):
    # 1. Сохраняем саму последовательность
    db_sequence = models.Sequence(
        name=sequence.name,
        description=sequence.description,
        raw_sequence=bio_calc.clean_sequence(sequence.raw_sequence), # Сразу чистим
        molecule_type=sequence.molecule_type,
        owner_id=current_user.id
    )
    database.add(db_sequence)
    database.commit()
    database.refresh(db_sequence)
    
    # 2. Считаем параметры
    gc = bio_calc.calculate_gc_content(db_sequence.raw_sequence)
    tm = bio_calc.calculate_melting_temp(db_sequence.raw_sequence)
    mw = bio_calc.calculate_molecular_weight(db_sequence.raw_sequence)
    
    # 3. Сохраняем результаты анализа и привязываем к сиквенсу
    db_analysis = models.AnalysisResult(
        sequence_id=db_sequence.id,
        gc_content=gc,
        melting_temp=tm,
        molecular_weight=mw
    )
    database.add(db_analysis)
    database.commit()
    
    # Обновляем объект, чтобы подтянуть анализ (благодаря relationship)
    database.refresh(db_sequence) 
    
    return db_sequence
