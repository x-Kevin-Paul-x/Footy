import unittest
from transfer import TransferMarket
from team import Team
from player import FootballPlayer
from manager_brain import ManagerBrain
from manager_profile import ManagerProfile
from manager import Manager

class TestTransferSystem(unittest.TestCase):
    def setUp(self):
        # Create test teams
        self.team_a = Team("Team A", budget=100000)
        self.team_b = Team("Team B", budget=5000000)

        # Create test players
        self.striker = FootballPlayer.create_player(position="ST")
        self.goalie = FootballPlayer.create_player(position="GK")
        self.midfielder = FootballPlayer.create_player(position="CM", age=31) # Average player
        self.midfielder.potential = 65 # Set potential *after* creation

        log_path = "transfer_logs\\debug_test_transfers.txt"

        # Initialize transfer market
        self.market = TransferMarket(log_path=log_path)

        # Create manager brain with debug mode
        self.profile = ManagerProfile()
        self.manager = Manager(profile=self.profile) # Use Manager, not ManagerBrain directly
        self.team_b.manager = self.manager  # Correctly assign the manager
        self.manager.team = self.team_b
        self.manager.set_debug(True) # Enable debug output

    def tearDown(self):
        """Close the log file after each test."""
        self.market.close_log()

    def test_player_valuation(self):
        """Test dynamic valuation calculation"""
        # Young player in prime position
        self.striker.age = 24
        val1 = self.market.calculate_player_value(self.striker)

        # Same player older
        self.striker.age = 31
        val2 = self.market.calculate_player_value(self.striker)

        print(f"Player value at 24: {val1}")
        print(f"Player value at 31: {val2}")

        self.assertLess(val2, val1, "Older player should have lower value")

    def test_transfer_workflow(self):
        """Test complete transfer lifecycle with detailed debugging."""
        print("\n--- Starting Transfer Workflow Test ---")

        # Add players to team_a first
        self.team_a.add_player(self.striker)
        self.team_a.add_player(self.goalie)
        self.team_a.add_player(self.midfielder)

        # Team A lists players
        listing1 = self.market.list_player(self.striker, self.team_a, asking_price=self.market.calculate_player_value(self.striker) * 0.89)  # High value
        listing2 = self.market.list_player(self.goalie, self.team_a, asking_price=self.market.calculate_player_value(self.goalie) * 0.99)   # Lower value
        listing3 = self.market.list_player(self.midfielder, self.team_a, asking_price=self.market.calculate_player_value(self.midfielder) * 0.99) # Mid value

        print(f"\n--- Players Listed on Transfer Market ---")
        print(f"Listing 1: {listing1.player.name}, Asking Price: {listing1.asking_price} , Value = {self.market.calculate_player_value(self.striker)}")
        print(f"Listing 2: {listing2.player.name}, Asking Price: {listing2.asking_price} , Value = {self.market.calculate_player_value(self.goalie)}")
        print(f"Listing 3: {listing3.player.name}, Asking Price: {listing3.asking_price} , Value = {self.market.calculate_player_value(self.midfielder)}")


        # Get possible actions for team_b's manager
        possible_actions = self.team_b.manager._get_possible_transfer_actions(self.market)
        print(f"\n--- Possible Actions for {self.team_b.manager.name}: ---")
        for action in possible_actions:
            print(action)

        # Get the manager's decision
        transfer_actions = self.team_b.manager.make_transfer_decision(self.market)
        print(f"\n--- Manager's Selected Transfer Actions: ---")
        print(transfer_actions)

        # Process transfer actions
        for action_type, *params in transfer_actions:
            if action_type == "buy":
                listing, offer = params
                print(f"\n--- Attempting to Buy Player: {listing.player.name} ---")
                print(f"  Offering: {offer}")
                print(f"  Team B Budget Before: {self.team_b.budget}")
                print(f"  Team A Budget Before: {self.team_a.budget}")

                success, message = self.market.make_transfer_offer(
                    self.team_b, listing, offer
                )

                print(f"  Transfer Success: {success}, Message: {message}")
                print(f"  Team B Budget After: {self.team_b.budget}")
                print(f"  Team A Budget After: {self.team_a.budget}")

                if success:
                    self.assertIn(listing.player, self.team_b.players)
                    self.assertNotIn(listing.player, self.team_a.players)
                    # Additional checks for budget and wage changes could be added here

        print("\n--- Transfer Workflow Test Complete ---")


if __name__ == "__main__":
    unittest.main()