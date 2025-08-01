# Enhanced api/user_routes.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from schemas.user_schemas import UserCreate, UserUpdate, UserRead, UserLogin
from crud import db_user
from core.database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/users", tags=["Users"])

@router.post("/", response_model=UserRead)
def create_user_api(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user"""
    try:
        return db_user.create_user(db=db, user=user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")

@router.get("/", response_model=List[UserRead])
def get_users_api(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Get all users with pagination"""
    if limit > 1000:
        raise HTTPException(status_code=400, detail="Limit cannot exceed 1000")
    return db_user.get_users(db=db, skip=skip, limit=limit)

@router.get("/{user_id}", response_model=UserRead)
def get_user_api(user_id: int, db: Session = Depends(get_db)):
    """Get a specific user by ID"""
    user = db_user.get_user_by_id(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}", response_model=UserRead)
def update_user_api(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update a user"""
    try:
        updated_user = db_user.update_user(db=db, user_id=user_id, user_update=user_update)
        if not updated_user:
            raise HTTPException(status_code=404, detail="User not found")
        return updated_user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")

@router.delete("/{user_id}")
def delete_user_api(user_id: int, db: Session = Depends(get_db)):
    """Delete a user"""
    try:
        deleted = db_user.delete_user(db=db, user_id=user_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="User not found")
        return {"success": True, "message": "User deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")

@router.get("/search/{query}")
def search_users_api(query: str, db: Session = Depends(get_db)):
    """Search users by name, email, or business name"""
    try:
        users = db_user.search_users(db=db, query=query)
        return {"success": True, "users": users}
    except Exception as e:
        logger.error(f"Error searching users: {e}")
        raise HTTPException(status_code=500, detail="Search failed")

@router.get("/stats/summary")
def get_user_stats_api(db: Session = Depends(get_db)):
    """Get user statistics"""
    try:
        stats = db_user.get_user_statistics(db=db)
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting user stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get statistics")

@router.post("/login")
def login_user_api(login_data: UserLogin, db: Session = Depends(get_db)):
    """Login user (basic implementation)"""
    try:
        user = db_user.get_user_by_email(db=db, email=login_data.email)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # In production, you would verify the hashed password
        # For now, direct comparison (NOT secure)
        if user.hashed_password != login_data.password:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        return {
            "success": True, 
            "message": "Login successful",
            "user": UserRead.from_orm(user)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@router.get("/email/{email}", response_model=UserRead)
def get_user_by_email_api(email: str, db: Session = Depends(get_db)):
    """Get user by email address"""
    user = db_user.get_user_by_email(db=db, email=email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user