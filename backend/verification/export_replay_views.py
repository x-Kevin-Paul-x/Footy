"""Export verified native recordings for the season's instant 2D viewer."""
import sys
import json
import time
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from logic.grf_trajectory import MatchTrajectory
from logic.grf_state_archive import GRFStateArchiveReader
from logic.replay.native_goal_frames import restore_native_goal_state
import gfootball.env as football_env

directory = Path(sys.argv[1])
output = Path(sys.argv[2]) if len(sys.argv) > 2 else directory.parents[2] / 'replay_views'
expected = int(sys.argv[3]) if len(sys.argv) > 3 else 380
output.mkdir(exist_ok=True)
env = football_env.create_environment(env_name='11_vs_11_kaggle', representation='raw',
    number_of_left_players_agent_controls=10, number_of_right_players_agent_controls=10,
    other_config_options={'action_set': 'full'})
env.reset()
try:
    while True:
        for path in sorted(directory.glob('*.npz')):
            target = output / (path.stem + '.json')
            audit = path.with_suffix('.audit.json')
            if target.exists() or not audit.exists() or not json.loads(audit.read_text())['passed']:
                continue
            trajectory = MatchTrajectory.load_from_npz(path)
            coords = np.concatenate([trajectory.player_coords.reshape(trajectory.total_steps, 44), trajectory.ball_coords], axis=1)
            coords = np.rint(coords * 10000).astype(int)
            frames = np.concatenate([coords, trajectory.scores, trajectory.game_mode[:, None]], axis=1).tolist()
            insertions = {}
            metadata = json.loads(path.with_suffix('.goals.json').read_text())
            with GRFStateArchiveReader(str(path.with_suffix('.goals.grfstate'))) as archive:
                for item in metadata['frames']:
                    observation = restore_native_goal_state(env, archive.get_state(item['index']))
                    coords = np.concatenate([np.asarray(observation['left_team']).reshape(-1),
                        np.asarray(observation['right_team']).reshape(-1), observation['ball']])
                    frame = np.rint(coords * 10000).astype(int).tolist() + list(observation['score']) + [int(observation['game_mode'])]
                    insertions.setdefault(str(item['step']), []).append(frame)
            manifest = trajectory.manifest
            target.write_text(json.dumps({'match_id': trajectory.match_id, 'home': manifest.home_team,
                'away': manifest.away_team, 'score': list(manifest.score), 'frames': frames,
                'goal_frames': insertions, 'events': manifest.events, 'players': manifest.home_players + manifest.away_players,
                'half_step': next(int(e['step']) for e in manifest.events if e['type'] == 'half_time'),
                'native_duration': manifest.engine_fingerprint['native_duration'],
                'display_coordinate_scale': 10000}, separators=(',', ':')))
        count = len(list(output.glob('*.json')))
        if count >= expected:
            print(f'EXPORTED_{expected}_NATIVE_REPLAYS', flush=True)
            break
        time.sleep(5)
finally:
    env.close()
