import datetime

from fastapi import HTTPException
from sqlalchemy import select, asc, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Contact, User
from src.schemas.Contacts_Schemas import ContactCreate, ContactUpdate


async def get_specific_contact_belongs_to_user(id: int, user: User, db: AsyncSession):
    q = select(Contact).where(Contact.user_id == user.id).filter(Contact.id == id)
    contact_data = await db.execute(q)
    contact = contact_data.scalar()
    return contact


async def repo_get_contacts(
    db: AsyncSession, user: User, limit: int, offset: int
) -> list[Contact]:
    contacts_data = (
        select(Contact)
        .where(Contact.user_id == user.id)
        .offset(offset)
        .limit(limit)
        .order_by(asc(Contact.id))
    )
    result = await db.execute(contacts_data)
    return result.scalars().all()


async def repo_get_contact_by_id(id: int, user: User, db: AsyncSession):
    contact = await get_specific_contact_belongs_to_user(id, user, db)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact


async def repo_create_new_contact(user: User, body: ContactCreate, db: AsyncSession):
    contact = Contact(**body.model_dump(), user_id=user.id)
    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    await db.commit()
    return contact


async def repo_update_contact_db(
    id: int, user: User, body: ContactUpdate, db: AsyncSession
):
    contact = await get_specific_contact_belongs_to_user(id, user, db)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)

    await db.commit()
    await db.refresh(contact)
    return contact


async def repo_delete_contact_db(id: int, user: User, db: AsyncSession):
    contact = await get_specific_contact_belongs_to_user(id, user, db)
    if contact is None:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact_name = f"{contact.first_name} {contact.last_name}"

    await db.delete(contact)
    await db.commit()

    return {"message": f'Contact "{contact_name}" successfully deleted'}


async def repo_get_contacts_query(
    user: User, query: str, limit: int, offset: int, db: AsyncSession
):
    search_query = f"%{query}%"
    lower_search_query = search_query.lower()

    q = (
        select(Contact)
        .where(
            (Contact.user_id == user.id)
            & (
                (func.lower(Contact.first_name).like(lower_search_query))
                | (func.lower(Contact.last_name).like(lower_search_query))
                | (func.lower(Contact.email).like(lower_search_query))
            )
        )
        .offset(offset)
        .limit(limit)
        .order_by(asc(Contact.id))
    )

    contacts_data = await db.execute(q)
    return contacts_data.scalars().all()


async def repo_get_upcoming_birthday_contacts(user: User, db: AsyncSession):
    today = datetime.datetime.now().date()
    end_date = today + datetime.timedelta(days=7)

    answer_contacts = []
    results = await db.execute(select(Contact).filter(Contact.user_id == user.id))
    contacts: list[Contact] = results.scalars().all()

    for contact in contacts:
        b_day = contact.b_day
        today_year_b_day = datetime.datetime(today.year, b_day.month, b_day.day).date()

        if today <= today_year_b_day <= end_date:
            answer_contacts.append(contact)

    return answer_contacts
