"""Redraw a restored GRF state without advancing simulation physics."""


def render_restored_native_frame(env):
    # GRF's Python render() returns its cached frame once rendering is enabled.
    # A state restore must explicitly redraw the native engine first.
    core = env.unwrapped._env
    core._env.game_config.render = True
    camera = getattr(env, '_footy_camera', None)
    if camera is not None:
        if not hasattr(core._env, 'set_presentation_camera'):
            raise RuntimeError('The Footy native visual runtime is required for camera presets')
        core._env.set_presentation_camera(*camera)
    core._env.render(True)
    core._retrieve_observation()
    # The native framebuffer is RGB (glReadPixels GL_RGB). GRF's Python
    # rgb_array wrapper swaps its red/blue channels in this supported runtime.
    # Read the freshly drawn framebuffer directly so club textures stay true.
    import numpy as np
    native = core._env
    if hasattr(native, 'get_frame'):
        width = native.game_config.render_resolution_x
        height = native.game_config.render_resolution_y
        # OpenGL's origin is bottom-left; presentation images use top-left.
        return np.frombuffer(native.get_frame(), dtype=np.uint8).reshape(height, width, 3)[::-1].copy()
    return env.render(mode='rgb_array')
