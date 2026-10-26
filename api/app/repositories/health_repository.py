from sqlalchemy import select
from sqlalchemy.orm import Session


def ping(db: Session) -> bool:
    return db.execute(select(1)).scalar_one() == 1
