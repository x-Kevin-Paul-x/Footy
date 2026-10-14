import copy
from types import SimpleNamespace
from logic.visual_identity import appearance_for_player, freeze_visual_identity, recorded_roster
from logic.grf_trajectory import MatchManifest
from logic.replay.camera_director import CameraDirector


def test_identity_is_persistent_and_does_not_touch_global_random_state():
    import random

    before = random.getstate()
    first = appearance_for_player(370, "Test Player")
    assert appearance_for_player(370, "Test Player") == first
    assert random.getstate() == before
    assert appearance_for_player(None, "Unknown") is None
    assert 1 <= first["skin"] <= 4


def test_clash_selection_and_frozen_player_metadata():
    roster = [{"player_id": 7, "name": "Test", "jersey_number": 47, "appearance": {"skin": 2}}]
    identity = freeze_visual_identity("Liverpool", "Bournemouth", roster, roster)
    assert identity["away"]["selected"] == "away"
    assert identity["home"]["goalkeeper"]["shirt"] != identity["away"]["goalkeeper"]["shirt"]
    manifest = MatchManifest.from_dict({"match_id": "test", "score": [2, 1], "visual_identity": identity})
    saved = manifest.to_dict()
    restored = MatchManifest.from_dict(copy.deepcopy(saved))
    assert restored.visual_identity == identity
    assert restored.visual_identity["home"]["roster"][0]["jersey_number"] == 47


def test_camera_director_uses_recorded_scorer_and_eases_transitions():
    manifest = SimpleNamespace(
        events=[{"type": "goal", "step": 100, "team": "home", "player": "Scorer"}],
        home_players=["Keeper", "Scorer"],
        away_players=["Away"],
    )
    director = CameraDirector(manifest, "director")
    assert director.at_step(99) == (1, -1, -1, 1.0)
    assert director.at_step(100) == (4, 0, 1, 0.0)
    assert director.at_step(105) == (4, 0, 1, 1.0)
    assert 0 < director.at_step(128)[3] < 1
    assert director.at_step(130) == (1, -1, -1, 1.0)
    manifest.events[0]["player"] = "Missing identity"
    assert CameraDirector(manifest, "director").at_step(105) == (1, -1, -1, 1.0)


def test_names_only_callers_and_frozen_identity_are_not_replaced_by_profile_defaults():
    from logic.footy_grf_adapter import GRFPlayerProfile

    profiles = [GRFPlayerProfile(name="Player", jersey_number=47, appearance={"skin": 2})]
    roster = recorded_roster(profiles, ["Recorded scorer"])
    frozen = freeze_visual_identity("Burnley", "Bournemouth", roster, [])
    profiles[0].appearance["skin"] = 4
    roster[0]["name"] = "Changed later"
    assert frozen["home"]["roster"][0]["name"] == "Recorded scorer"
    assert frozen["home"]["roster"][0]["appearance"] == {"skin": 2}
