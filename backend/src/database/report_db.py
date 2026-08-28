import json
from datetime import datetime
from database.session import SessionLocal, get_db_session
from database.models import SeasonReport, TransferReport

def save_season_report_to_db(season_year: int, champion_team: str, report_data: dict, db_file=None):
    """Inserts or updates a season report in the SeasonReport table."""
    with get_db_session() as db:
        report = db.query(SeasonReport).filter(SeasonReport.season_year == season_year).first()
        if report:
            report.champion_team = champion_team
            report.report_data = json.dumps(report_data, default=str)
            report.created_at = datetime.now().isoformat()
        else:
            report = SeasonReport(
                season_year=season_year,
                champion_team=champion_team,
                report_data=json.dumps(report_data, default=str),
                created_at=datetime.now().isoformat()
            )
            db.add(report)
        db.flush()
        return report.report_id

def get_all_season_reports(db_file=None):
    """Retrieves all season reports."""
    db = SessionLocal()
    try:
        reports = db.query(SeasonReport).order_by(SeasonReport.season_year.desc()).all()
        return [(r.report_id, r.season_year, r.champion_team, r.created_at) for r in reports]
    finally:
        db.close()

def get_season_report_by_year(season_year: int, db_file=None):
    """Retrieves a specific season report by year."""
    db = SessionLocal()
    try:
        report = db.query(SeasonReport).filter(SeasonReport.season_year == season_year).first()
        if report:
            return json.loads(report.report_data)
        return None
    finally:
        db.close()

def save_transfer_report_to_db(season_year: int, report_data: dict, db_file=None):
    """Inserts or updates a transfer report in the TransferReport table."""
    with get_db_session() as db:
        report = db.query(TransferReport).filter(TransferReport.season_year == season_year).first()
        if report:
            report.report_data = json.dumps(report_data, default=str)
            report.created_at = datetime.now().isoformat()
        else:
            report = TransferReport(
                season_year=season_year,
                report_data=json.dumps(report_data, default=str),
                created_at=datetime.now().isoformat()
            )
            db.add(report)
        db.flush()
        return report.report_id

def get_all_transfer_reports(db_file=None):
    """Retrieves all transfer reports."""
    db = SessionLocal()
    try:
        reports = db.query(TransferReport).order_by(TransferReport.season_year.desc()).all()
        return [(r.report_id, r.season_year, r.created_at) for r in reports]
    finally:
        db.close()

def get_transfer_report_by_year(season_year: int, db_file=None):
    """Retrieves a specific transfer report by year."""
    db = SessionLocal()
    try:
        report = db.query(TransferReport).filter(TransferReport.season_year == season_year).first()
        if report:
            return json.loads(report.report_data)
        return None
    finally:
        db.close()
