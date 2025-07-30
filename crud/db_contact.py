from sqlalchemy.orm import Session
from fastapi import HTTPException
from models.contact import Contact
from schemas.contact_schemas import ContactCreate, ContactUpdate, ContactBatchCreate
from utils.validators import validate_phone_number

def create_contact(db: Session, contact: ContactCreate):
    """
    Validates a new contact's data and creates it in the database.
    """
    # Step 1: Validate the phone number before proceeding.
    if not validate_phone_number(contact.phone_number):
        # If invalid, raise an error that the API can return to the user.
        raise HTTPException(status_code=400, detail=f"Invalid phone number format: {contact.phone_number}")

    # Step 2: If validation passes, create the database object.
    db_contact = Contact(**contact.model_dump())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def get_contact(db: Session, contact_id: int):
    return db.query(Contact).filter(Contact.id == contact_id).first()

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Contact).offset(skip).limit(limit).all()

def get_contacts_by_ids(db: Session, contact_ids: list[int]):
    if not contact_ids:
        return []
    return db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

def create_contact(db: Session, contact: ContactCreate):
    db_contact = Contact(**contact.model_dump())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def update_contact(db: Session, contact_id: int, contact_update: ContactUpdate):
    db_contact = get_contact(db, contact_id)
    if db_contact:
        update_data = contact_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_contact, key, value)
        db.commit()
        db.refresh(db_contact)
    return db_contact

def delete_contact(db: Session, contact_id: int):
    db_contact = get_contact(db, contact_id)
    if db_contact:
        db.delete(db_contact)
        db.commit()
    return db_contact