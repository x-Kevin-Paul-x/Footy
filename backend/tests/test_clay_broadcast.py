import copy
import numpy as np
import pytest
from logic.team_identity import club_colour
from logic.grf_renderer import draw_pre_match_card, draw_studio_stats_card
from logic.grf_trajectory import MatchManifest
from logic.footy_grf_adapter import FootyGRFAdapter


def test_club_aliases_and_legacy_fallback():
    assert club_colour("Burnley FC", "#2196f3") == "#6C1D45"
    assert club_colour("AFC Bournemouth") == "#DA291C"
    assert club_colour("Man City") == club_colour("Manchester City")
    assert club_colour("Custom Club", "#abcdef") == "#abcdef"
    assert club_colour("Custom Club") == club_colour("Custom Club")


def test_profile_preserves_persistent_identity_and_assigned_position():
    profile = FootyGRFAdapter.extract_player_profile(
        {"id": 234, "name": "Test Player", "jersey_number": 47, "position": "CM"}, "RM"
    )
    assert (profile.player_id, profile.jersey_number, profile.assigned_position) == (234, 47, "RM")
    assert profile.position == "CM"  # Presentation metadata must not alter existing policy inputs.


@pytest.mark.parametrize("resolution", [(1280, 720), (1920, 1080), (3840, 2160)])
@pytest.mark.parametrize("theme", ["dark", "light"])
def test_cards_scale_and_do_not_mutate_recorded_results(resolution, theme):
    w, h = resolution
    events = [{"type": "goal", "minute": 34, "player": "Test Player", "team": "home"}]
    before = copy.deepcopy(events)
    frame = draw_studio_stats_card(
        w=w,
        h=h,
        theme=theme,
        home_team="Burnley",
        away_team="Bournemouth",
        score=(1, 0),
        events=events,
        h_poss=None,
        a_poss=None,
    )
    assert frame.shape == (h, w, 3) and frame.dtype == np.uint8
    assert events == before
    assert frame.var() > 100


def test_legacy_number_is_unknown_and_real_number_changes_card():
    legacy = draw_pre_match_card(home_team="Burnley", home_players=["Test Player"])
    recorded = draw_pre_match_card(
        home_team="Burnley",
        home_players=["Test Player"],
        home_roster=[{"player_id": 234, "jersey_number": 47, "position": "GK"}],
    )
    assert np.any(legacy != recorded)
    manifest = MatchManifest.from_dict(
        {"match_id": "legacy", "home_team": "Burnley", "away_team": "Bournemouth", "score": [2, 1]}
    )
    assert manifest.home_roster == []
    assert "home_roster" not in manifest.to_dict()
    manifest.home_roster = [{"player_id": 234, "jersey_number": 47, "position": "GK"}]
    restored = MatchManifest.from_dict(manifest.to_dict())
    assert restored.home_roster == manifest.home_roster
    assert restored.score == (2, 1)
