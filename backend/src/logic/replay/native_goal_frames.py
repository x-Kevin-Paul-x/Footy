"""Show native goal states that GRF's public step skips before the restart."""
import json
from pathlib import Path
import numpy as np
import cv2
from logic.grf_state_archive import GRFStateArchiveReader, ReplayIntegrityError
from logic.grf_renderer import draw_hud
from .grf_render_runtime import render_restored_native_frame


def restore_native_goal_state(env, state):
    core = env.unwrapped._env
    retrieve = core._retrieve_observation
    def retrieve_stopped_state():
        retrieve()
        return True
    core._retrieve_observation = retrieve_stopped_state
    try:
        env.set_state(state)
    finally:
        core._retrieve_observation = retrieve
    return env.observation()[0]


class NativeGoalFrames:
    def __init__(self, states_file, match_id, trajectory):
        self.archive = None
        self.by_step = {}
        meta_path = Path(states_file).with_suffix('.goals.json')
        archive_path = Path(states_file).with_suffix('.goals.grfstate')
        if not meta_path.exists():
            return
        metadata = json.loads(meta_path.read_text())
        if metadata['match_id'] != match_id:
            raise ReplayIntegrityError('Native goal frames belong to a different match')
        frames = metadata['frames']
        self.archive = GRFStateArchiveReader(str(archive_path))
        self.archive.validate(expected_match_id=match_id, expected_steps=len(frames), check_global_sha=True)
        goals = {int(e['step']) for e in trajectory.manifest.events if e['type'] == 'goal'} if trajectory else set()
        for item in frames:
            step = int(item['step'])
            if trajectory is not None and (step not in goals or not np.array_equal(item['score'], trajectory.scores[step])):
                raise ReplayIntegrityError('Native goal frame disagrees with the canonical result')
            self.by_step.setdefault(step, []).append(item)

    def render_before(self, step, env, width, height, home_team, away_team, home_bgr, away_bgr, duration, half_step):
        for item in self.by_step.get(step, []):
            # GRF normally asserts that restored states are in play. Goal
            # celebration states intentionally are stopped; restore them only
            # for rendering, with no simulation steps or policy actions.
            observation = restore_native_goal_state(env, self.archive.get_state(item['index']))
            if (not np.allclose(observation['ball'], item['ball'], rtol=0, atol=1e-6)
                    or not np.array_equal(observation['score'], item['score'])):
                raise ReplayIntegrityError('Restored native goal frame diverges')
            frame = render_restored_native_frame(env)
            if frame.shape[:2] != (height, width):
                frame = cv2.resize(frame, (width, height))
            minute = max(1, min(90, int((duration - item['steps_left']) * 90 / duration) + 1))
            frame = draw_hud(frame=cv2.cvtColor(frame, cv2.COLOR_RGB2BGR),
                             home_team=home_team, away_team=away_team, score=tuple(observation['score']),
                             match_min=minute, home_bgr=home_bgr, away_bgr=away_bgr,
                             is_second_half=step >= half_step,
                             match_seconds=(duration - item['steps_left']) * 5400 / duration)
            yield cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def close(self):
        if self.archive:
            self.archive.close()
