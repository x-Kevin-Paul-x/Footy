"""Transfer business queries use the same ORM session as the other repositories."""
from sqlalchemy.orm import aliased

from database.models import Player, Team, TransferHistory, TransferListing
from database.session import get_db_session


def season_transfers(year, run_id=None):
    seller, buyer = aliased(Team), aliased(Team)
    with get_db_session() as db:
        query = db.query(TransferHistory, Player.name, seller.name, buyer.name).outerjoin(
            Player, Player.player_id == TransferHistory.player_id).outerjoin(
            seller, seller.team_id == TransferHistory.from_team_id).outerjoin(
            buyer, buyer.team_id == TransferHistory.to_team_id).filter(
            TransferHistory.season_year == year)
        if run_id:
            query = query.filter(TransferHistory.simulation_run_id == run_id)
        rows = query.order_by(TransferHistory.transfer_id).all()
        return [{'transfer_id': t.transfer_id, 'player_id': t.player_id, 'player': p or f'player[{t.player_id}]',
                 'from_team_id': t.from_team_id, 'from_team': f or 'Free agent', 'to_team_id': t.to_team_id,
                 'to_team': b or 'Free agent', 'amount': t.amount, 'day': t.day, 'season_year': year}
                for t, p, f, b in rows]


def record_transfer(player_id, from_team_id, to_team_id, amount, day, year, listing_id=None, run_id=None):
    with get_db_session() as db:
        row = TransferHistory(player_id=player_id, from_team_id=from_team_id, to_team_id=to_team_id,
                              amount=amount, day=day, season_year=year, simulation_run_id=run_id)
        db.add(row)
        if listing_id is not None:
            db.query(TransferListing).filter(TransferListing.listing_id == listing_id).delete()


def record_listing(listing):
    with get_db_session() as db:
        if db.get(TransferListing, listing.listing_id) is None:
            db.add(TransferListing(listing_id=listing.listing_id, player_id=listing.player.player_id,
                                   selling_team_id=listing.selling_team.team_id,
                                   asking_price=listing.asking_price, listed_date=listing.listed_date,
                                   expires_in=listing.expires_in))
