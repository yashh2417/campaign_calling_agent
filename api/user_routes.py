from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.user_schemas import UserCreate, UserRead
from crud import db_user  # You will need to create this file
from core.database import get_db

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("/", response_model=UserRead)
def create_user_api(user: UserCreate, db: Session = Depends(get_db)):
    """
    Creates a new user.
    """
    # You'll need a function to hash the password before saving
    # For now, we'll assume a simple pass-through for demonstration
    return db_user.create_user(db=db, user=user)