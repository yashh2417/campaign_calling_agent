from sqlalchemy.orm import Session
from models.user import User
from schemas.user_schemas import UserCreate
# In a real app, you would use a password hashing library
# from passlib.context import CryptContext
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, user: UserCreate):
    # In a real app, you would hash the password like this:
    # hashed_password = pwd_context.hash(user.password)
    # For now, we'll store it directly (NOT for production)
    db_user = User(
        name=user.name,
        email=user.email,
        phone_number=user.phone_number,
        hashed_password=user.password, # This should be hashed
        business_name=user.business_name,
        business_details=user.business_details
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user