from sqlalchemy.orm import Session
from sqlalchemy import or_
from models.contact import Contact
from schemas.contact_schemas import ContactCreate, ContactUpdate, ContactBatchCreate
from utils.validators import validate_phone_number
import logging

logger = logging.getLogger(__name__)

def create_contact(db: Session, contact: ContactCreate):
    """
    Validates a new contact's data and creates it in the database.
    """
    # Step 1: Validate the phone number before proceeding.
    if not validate_phone_number(contact.phone_number):
        # If invalid, raise an error that the API can return to the user.
        raise ValueError(f"Invalid phone number format: {contact.phone_number}")

    # Step 2: Check for duplicate phone numbers
    existing_contact = db.query(Contact).filter(Contact.phone_number == contact.phone_number).first()
    if existing_contact:
        raise ValueError(f"Contact with phone number {contact.phone_number} already exists")

    # Step 3: If validation passes, create the database object.
    db_contact = Contact(**contact.model_dump())
    db.add(db_contact)
    db.commit()
    db.refresh(db_contact)
    return db_contact

def validate_and_create_contact(db: Session, contact: ContactCreate):
    """
    Validates and creates a contact with better error handling for batch operations
    """
    try:
        return create_contact(db, contact)
    except ValueError as e:
        # Re-raise ValueError for validation errors
        raise e
    except Exception as e:
        logger.error(f"Database error creating contact: {e}")
        raise ValueError("Database error occurred")

def get_contact(db: Session, contact_id: int):
    return db.query(Contact).filter(Contact.id == contact_id).first()

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Contact).offset(skip).limit(limit).all()

def get_contacts_by_ids(db: Session, contact_ids: list[int]):
    if not contact_ids:
        return []
    return db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

def update_contact(db: Session, contact_id: int, contact_update: ContactUpdate):
    db_contact = get_contact(db, contact_id)
    if db_contact:
        update_data = contact_update.model_dump(exclude_unset=True)
        
        # Validate phone number if it's being updated
        if 'phone_number' in update_data:
            if not validate_phone_number(update_data['phone_number']):
                raise ValueError(f"Invalid phone number format: {update_data['phone_number']}")
            
            # Check for duplicates (excluding current contact)
            existing = db.query(Contact).filter(
                Contact.phone_number == update_data['phone_number'],
                Contact.id != contact_id
            ).first()
            if existing:
                raise ValueError(f"Phone number {update_data['phone_number']} is already in use")
        
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
        return True
    return False

def search_contacts(db: Session, query: str):
    """Search contacts by name, phone, or company"""
    search_term = f"%{query}%"
    return db.query(Contact).filter(
        or_(
            Contact.name.ilike(search_term),
            Contact.phone_number.ilike(search_term),
            Contact.company_name.ilike(search_term),
            Contact.email.ilike(search_term)
        )
    ).all()

def get_contact_statistics(db: Session):
    """Get contact statistics"""
    total_contacts = db.query(Contact).count()
    contacts_with_company = db.query(Contact).filter(Contact.company_name.isnot(None)).count()
    contacts_with_email = db.query(Contact).filter(Contact.email.isnot(None)).count()
    
    return {
        "total_contacts": total_contacts,
        "contacts_with_company": contacts_with_company,
        "contacts_with_email": contacts_with_email,
        "contacts_without_company": total_contacts - contacts_with_company,
        "contacts_without_email": total_contacts - contacts_with_email
    }