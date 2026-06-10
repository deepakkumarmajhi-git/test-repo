from sqlalchemy import Integer, String, Column, ForeignKey, TIMESTAMP, func
from sqlalchemy.orm import relationship
from database import Base

class Repo(Base):
    __tablename__ = "repos"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    name = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="repos")
    commits = relationship("Commit", back_populates="repo")
