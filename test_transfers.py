import unittest
from transfer import TransferMarket
from team import Team
from player import FootballPlayer
from manager_brain import ManagerBrain
from manager_profile import ManagerProfile
from manager import Manager
from manager import Manager
class TestTransferSystem(unittest.TestCase):
    def setUp(self):
        # Create test teams
        self.team_a = Team("Team A", budget=10000000)
        self.team_b = Team("Team B", budget=5000000)
        
        # Create test players
        self.striker = FootballPlayer.create_player(position="ST")
        self.goalie = FootballPlayer.create_player(position="GK")
        
        # Initialize transfer market
        self.market = TransferMarket()
        
        # Create manager brain with debug mode
        self.profile = ManagerProfile()
        self.manager = ManagerBrain(self.profile)
        self.team_b.manager = Manager(profile=self.profile)
        self.team_b.manager.team = self.team_b
    
    def test_player_valuation(self):
        """Test dynamic valuation calculation"""
        # Young player in prime position
        self.striker.age = 24
        val1 = self.market.calculate_player_value(self.striker)
        
        # Same player older
        self.striker.age = 31
        val2 = self.market.calculate_player_value(self.striker)
        
        self.assertLess(val2, val1, "Older player should have lower value")

    def test_transfer_workflow(self):
        """Test complete transfer lifecycle"""
        # Add striker to team_a first
        self.team_a.add_player(self.striker)
        
        # Team A lists a player
        listing = self.market.list_player(self.striker, self.team_a)
        
        # Set reasonable asking price for test
        listing.asking_price = self.team_b.transfer_budget * 0.5  # 50% of available budget
        
        # Manager decides on transfer
        transfer_actions = self.team_b.manager.make_transfer_decision(self.market)
        
        # Process transfer actions
        for action_type, *params in transfer_actions:
            if action_type == "buy":
                listing, offer = params
                success, _ = self.market.make_transfer_offer(
                    self.team_b, listing, offer
                )
            self.assertTrue(success)
            self.assertIn(self.striker, self.team_b.players)
            self.assertLess(self.team_b.budget, 5000000)

if __name__ == "__main__":
    unittest.main()