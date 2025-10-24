"""Base service layer utilities."""
class BaseService:
    """Lightweight base class for service objects.

    Holds a SQLAlchemy `Session` for DB operations.
    """
    def __init__(self, session):
        """Initialize the service with a database session.

        Args:
            session: Active SQLAlchemy session to use for queries and writes.
        """
        self.session = session

