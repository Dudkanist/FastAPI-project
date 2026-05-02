from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from . import models, schemas, auth, db

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

@app.get("/", tags=["Healthcheck"])
async def root():
    return {"status": "alive", "database": "connected"}
