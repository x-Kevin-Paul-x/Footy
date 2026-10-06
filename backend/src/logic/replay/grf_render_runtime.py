"""Redraw a restored GRF state without advancing simulation physics."""


def render_restored_native_frame(env):
    # GRF's Python render() returns its cached frame once rendering is enabled.
    # A state restore must explicitly redraw the native engine first.
    core = env.unwrapped._env
    core._env.game_config.render = True
    core._env.render(True)
    core._retrieve_observation()
    return env.render(mode='rgb_array')
