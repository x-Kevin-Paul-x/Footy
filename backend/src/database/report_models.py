from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime
from database.models import Base

class SeasonReport(Base):
    __tablename__ = 'SeasonReport'
    report_id = Column(Integer, primary_key=True, autoincrement=True)
    season_year = Column(Integer, nullable=False, unique=True)
    champion_team = Column(String, nullable=False)
    report_data = Column(JSON, nullable=False)
    created_at = Column(String, default=lambda: datetime.now().isoformat())

class TransferReport(Base):
    __tablename__ = 'TransferReport'
    report_id = Column(Integer, primary_key=True, autoincrement=True)
    season_year = Column(Integer, nullable=False, unique=True)
    report_data = Column(JSON, nullable=False)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
