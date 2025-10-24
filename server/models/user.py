"""User ORM model.

Represents an application user who can rate movies.
"""


from typing import TYPE_CHECKING

from sqlalchemy.orm import Mapped, mapped_column, relationship

from server.models.base import BaseSQLModel

if TYPE_CHECKING:
    from server.models.ratings import RatingModel
else:
    RatingModel = "RatingModel"


class UserModel(BaseSQLModel):
    """A single user of the application.

    Attributes:
        user_id: Retrieves primary key.
        ratings: All ratings rated by this user.
    """
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key = True, autoincrement = True)

    # Relationships
    ratings: Mapped[list[RatingModel]] = relationship(
        back_populates = "user", cascade = "all, delete-orphan"
    )
