from sqlalchemy.orm import Session
from models.user import User
from auth import hash_password
import uuid

class UserRepository:
    @staticmethod
    def create_user(db: Session, username: str, email: str, password: str) -> User:
        """Create a new user."""
        hashed_password = hash_password(password)
        user = User(
            id=uuid.uuid4(),
            username=username,
            email=email,
            password_hash=hashed_password
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def get_user_by_username(db: Session, username: str) -> User | None:
        """Get a user by username."""
        return db.query(User).filter(User.username == username).first()
    
    @staticmethod
    def get_user_by_email(db: Session, email: str) -> User | None:
        """Get a user by email."""
        return db.query(User).filter(User.email == email).first()
    
    @staticmethod
    def get_user_by_id(db: Session, user_id: str) -> User | None:
        """Get a user by ID."""
        return db.query(User).filter(User.id == user_id).first()

user_repo = UserRepository()
