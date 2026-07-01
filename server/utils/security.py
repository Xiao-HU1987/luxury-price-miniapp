from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def _decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def get_current_principal(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的登录凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not token:
        raise credentials_exception

    try:
        payload = _decode_token(token)
        subject = payload.get("sub")
        role = payload.get("role") or "user"
        if subject is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if role == "admin" or (isinstance(subject, str) and subject.startswith("admin:")):
        return {
            "role": "admin",
            "subject": subject,
            "user": None,
        }

    user = db.query(User).filter(User.user_id == subject).first()
    if user is None:
        raise credentials_exception
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )

    return {
        "role": "user",
        "subject": subject,
        "user": user,
    }


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    principal = get_current_principal(token=token, db=db)
    if principal["role"] != "user" or not principal.get("user"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的登录凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal["user"]


def get_current_admin(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> dict:
    principal = get_current_principal(token=token, db=db)
    if principal["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无管理员权限"
        )
    return principal


def get_current_user_optional(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = _decode_token(token)
        user_id: str = payload.get("sub")
        role = payload.get("role") or "user"
        if user_id is None or role == "admin" or (isinstance(user_id, str) and user_id.startswith("admin:")):
            return None
    except JWTError:
        return None
    user = db.query(User).filter(User.user_id == user_id).first()
    if user and user.status == "active":
        return user
    return None
