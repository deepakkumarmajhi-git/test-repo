from sqlalchemy import Integer, String, Column, ForeignKey, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from database import Base

class Commit(Base):
    __tablename__ = "commits"
    
    id = Column(Integer, primary_key=True, index=True)
    repo_id = Column(Integer, ForeignKey("repos.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    branch = Column(String, nullable=False)
    message = Column(JSONB, nullable=False)
    total_commit = Column(Integer, nullable=False)
    timestamp = Column(TIMESTAMP, server_default=func.now())

    repo = relationship("Repo", back_populates="commits")
    user = relationship("User", back_populates="commits")
