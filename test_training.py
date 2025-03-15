import sys
from player import FootballPlayer

def test_training():
    print("\n=== Starting Training Test ===")
    
    # Create test player
    player = FootballPlayer("Test Player", 25, "CM")
    
    print("\nTest Case 1: Basic training session")
    print(f"Initial fitness: {player.stats['fitness']}")
    results = player.train_player(
        intensity="medium",
        training_days=3,
        coach_bonus=0.5
    )
    print(f"Final fitness: {player.stats['fitness']}")
    
    print("\nTest Case 2: Overtraining (low fitness)")
    player.stats["fitness"] = 20  # Force low fitness
    results = player.train_player(
        intensity="high",
        training_days=5,
        coach_bonus=0.2
    )
    
    print("\n=== Training Test Complete ===")

if __name__ == "__main__":
    test_players = [
        FootballPlayer.create_player(position="GK"),
        FootballPlayer.create_player(position="CB"),
        FootballPlayer.create_player(position="ST")
    ]
    
    for p in test_players:
        print(f"\nTesting {p.position} player: {p.name}")
        p.train_player("high", training_days=2, coach_bonus=0.7)
        print(f"Potential after training: {p.potential:.1f}")
    
    test_training()