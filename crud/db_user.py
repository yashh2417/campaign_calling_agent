# Enhanced crud/db_user.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.user import User
from schemas.user_schemas import UserCreate, UserUpdate
import logging
# In a real app, you would use a password hashing library
# from passlib.context import CryptContext
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = logging.getLogger(__name__)

def get_user_by_email(db: Session, email: str):
    """Get user by email address"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_phone(db: Session, phone_number: str):
    """Get user by phone number"""
    return db.query(User).filter(User.phone_number == phone_number).first()

def get_user_by_id(db: Session, user_id: int):
    """Get user by ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Get all users with pagination"""
    return db.query(User).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate):
    """Create a new user with validation"""
    # Check for existing email
    existing_email = get_user_by_email(db, user.email)
    if existing_email:
        raise ValueError(f"User with email {user.email} already exists")
    
    # Check for existing phone number
    existing_phone = get_user_by_phone(db, user.phone_number)
    if existing_phone:
        raise ValueError(f"User with phone number {user.phone_number} already exists")
    
    # In a real app, you would hash the password like this:
    # hashed_password = pwd_context.hash(user.password)
    # For now, we'll store it directly (NOT for production)
    db_user = User(
        name=user.name,
        email=user.email,
        phone_number=user.phone_number,
        hashed_password=user.password,  # This should be hashed
        business_name=user.business_name,
        business_details=user.business_details
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user(db: Session, user_id: int, user_update: UserUpdate):
    """Update user information"""
    db_user = get_user_by_id(db, user_id)
    if not db_user:
        return None
    
    update_data = user_update.model_dump(exclude_unset=True)
    
    # Check for email conflicts if email is being updated
    if 'email' in update_data and update_data['email'] != db_user.email:
        existing_email = get_user_by_email(db, update_data['email'])
        if existing_email and existing_email.id != user_id:
            raise ValueError(f"Email {update_data['email']} is already in use")
    
    # Check for phone number conflicts if phone is being updated
    if 'phone_number' in update_data and update_data['phone_number'] != db_user.phone_number:
        existing_phone = get_user_by_phone(db, update_data['phone_number'])
        if existing_phone and existing_phone.id != user_id:
            raise ValueError(f"Phone number {update_data['phone_number']} is already in use")
    
    # Hash password if it's being updated
    if 'password' in update_data:
        # In production: update_data['hashed_password'] = pwd_context.hash(update_data['password'])
        update_data['hashed_password'] = update_data.pop('password')
    
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int):
    """Delete a user"""
    db_user = get_user_by_id(db, user_id)
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False

def search_users(db: Session, query: str):
    """Search users by name, email, or business name"""
    search_term = f"%{query}%"
    return db.query(User).filter(
        or_(
            User.name.ilike(search_term),
            User.email.ilike(search_term),
            User.business_name.ilike(search_term)
        )
    ).all()

def get_user_statistics(db: Session):
    """Get user statistics"""
    total_users = db.query(User).count()
    users_with_business = db.query(User).filter(User.business_name.isnot(None)).count()
    
    return {
        "total_users": total_users,
        "users_with_business": users_with_business,
        "users_without_business": total_users - users_with_business
    }