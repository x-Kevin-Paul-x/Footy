import pytest

from logic.broadcast.config import BroadcastRenderConfig
from logic.broadcast.schema import (
    BroadcastArtifactMetadata,
    BroadcastPlan,
    CameraCue,
    GraphicsCue,
    ReplayCue,
)
from config import (
    ALTERNATE_REPLAYS_ENABLED,
    BROADCAST_V2_ENABLED,
    CAMERA_DIRECTOR_ENABLED,
    CELEBRATIONS_ENABLED,
    PRESENTATION_FPS,
)


def test_broadcast_feature_switches_have_legacy_safe_defaults():
    assert BROADCAST_V2_ENABLED is False
    assert CAMERA_DIRECTOR_ENABLED is False
    assert PRESENTATION_FPS == 30
    assert ALTERNATE_REPLAYS_ENABLED is False
    assert CELEBRATIONS_ENABLED is False


def test_broadcast_schema_serialization_is_stable_and_immutable():
    graphics = GraphicsCue(source_step=12, graphic="goal_lower_third", payload={"scorer": "Player 8", "nested": {"score": [1, 0]}})
    plan = BroadcastPlan(
        match_id="fixture_1",
        source_state_rate=10.0,
        presentation_fps=30,
        camera_cues=(CameraCue(source_step=12, mode="SCORER", reason="goal"),),
        graphics_cues=(graphics,),
        replay_cues=(ReplayCue(source_step=12, start_step=2, end_step=12, speed=0.5, label="goal"),),
    )
    equivalent = BroadcastPlan(
        match_id="fixture_1",
        source_state_rate=10.0,
        presentation_fps=30,
        camera_cues=(CameraCue(source_step=12, mode="SCORER", reason="goal"),),
        graphics_cues=(GraphicsCue(source_step=12, graphic="goal_lower_third", payload={"nested": {"score": [1, 0]}, "scorer": "Player 8"}),),
        replay_cues=(ReplayCue(source_step=12, start_step=2, end_step=12, speed=0.5, label="goal"),),
    )

    assert plan.to_json() == equivalent.to_json()
    assert plan.sha256() == equivalent.sha256()
    with pytest.raises(TypeError):
        graphics.payload["scorer"] = "mutated"
    with pytest.raises(TypeError):
        graphics.payload["nested"]["score"] = (9, 9)


def test_broadcast_metadata_and_config_are_presentation_only_and_stable():
    config = BroadcastRenderConfig()
    metadata = BroadcastArtifactMetadata(
        renderer_version="broadcast-v2-phase1",
        timeline_version="not-planned",
        camera_profile="legacy",
        presentation_fps=30,
        resolution=(1280, 720),
        encoder="not-planned",
        source_archive_sha256="archive-sha",
        broadcast_config_sha256=config.sha256(),
    )

    assert config.to_dict()["presentation_fps"] == 30
    assert metadata.to_json() == metadata.to_json()
    assert metadata.to_dict()["broadcast_config_sha256"] == config.sha256()
