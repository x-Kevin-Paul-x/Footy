"""Build Footy's visual bindings from an existing compatible GRF source checkout.

Never edits or installs over that checkout. Output stays under ignored runtime/.
Run with the same Linux Python version as the installed GRF extension.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


def replace(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"Unsupported GRF source at {path}: patch anchor is not unique")
    path.write_text(text.replace(old, new))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="GRF third_party/gfootball_engine source directory")
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--incremental", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent / "runtime" / "visual"
    source = root / "source"
    if source.exists():
        if not args.incremental:
            raise RuntimeError("Build source already exists; use --incremental to rebuild it")
        build = root / "build"
        subprocess.run(["cmake", "-S", str(source), "-B", str(build)], check=True)
        subprocess.run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], check=True)
        shutil.copy2(build / "libgame.so", root / "_gameplayfootball.building.so")
        os.replace(root / "_gameplayfootball.building.so", root / "_gameplayfootball.so")
        return
    root.mkdir(parents=True, exist_ok=True)
    ignore_build = shutil.ignore_patterns(
        "CMakeFiles",
        "CMakeCache.txt",
        "*.o",
        "*.so",
        "*.a",
        "Makefile",
        "cmake_install.cmake",
        "__pycache__",
        "lib",
        ".git",
        "gfootball_engine",
    )

    def ignore(directory, entries):
        ignored = set(ignore_build(directory, entries))
        if Path(directory) == args.source:
            ignored.update({"data", "fonts"})
        return ignored

    shutil.copytree(args.source, source, ignore=ignore)
    # Some compatible local GRF trees contain a stale debug-number accessor.
    # This changes only the optional 2D debug label, never player mechanics.
    player = source / "src/onthepitch/player/player.cpp"
    if "int pId = GetID() % 11;" in player.read_text():
        replace(player, "int pId = GetID() % 11;", "int pId = GetStableID() % 11;")
    hashes = {
        str(p.relative_to(source)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob("*") if p.is_file()
    }
    replace(
        source / "src/data/playerdata.hpp",
        "    std::string GetLastName() const { return lastName; }",
        "    std::string GetLastName() const { return lastName; }\n"
        "    void SetPresentationName(const std::string& name) { lastName = name; }",
    )
    humanoid = source / "src/onthepitch/player/humanoid/humanoidbase"
    replace(
        humanoid.with_suffix(".hpp"),
        "    void SetKit(boost::intrusive_ptr < Resource<Surface> > newKit);",
        "    void SetKit(boost::intrusive_ptr < Resource<Surface> > newKit);\n"
        "    void ApplyVisualIdentity(const std::string& kit, int skin, const std::string& hair, const std::string& colour);\n"
        "    void ApplyPresentationClip(const std::string& path, int frame);",
    )
    with humanoid.with_suffix(".cpp").open("a") as out:
        out.write((Path(__file__).with_name("visual_identity.cpp.inc")).read_text())
    match = source / "src/onthepitch/match"
    replace(
        match.with_suffix(".cpp"),
        "  scoreboard->SetTimeStr(timeStr);",
        "  scoreboard->SetTimeStr(timeStr);\n  scoreboard->Hide();",
    )
    replace(match.with_suffix(".cpp"), "  radar->Put();", "  radar->Put();\n  radar->Hide();")
    replace(
        match.with_suffix(".hpp"),
        "    void UpdateIngameCamera();",
        "    void UpdateIngameCamera(int method = 1, int focusTeam = -1, int focusPlayer = -1, float blend = 1.0f);",
    )
    replace(
        match.with_suffix(".cpp"),
        "void Match::UpdateIngameCamera() {",
        "void Match::UpdateIngameCamera(int method, int focusTeam, int focusPlayer, float blend) {",
    )
    replace(
        match.with_suffix(".cpp"),
        "  int camMethod = 1; // 1 == wide, 2 == birds-eye, 3 == tele",
        "  auto previousOrientation = cameraOrientation;\n"
        "  auto previousNodeOrientation = cameraNodeOrientation;\n"
        "  auto previousPosition = cameraNodePosition;\n"
        "  float previousFOV = cameraFOV;\n"
        "  int camMethod = method == 4 ? 3 : method;\n"
        "  if (focusTeam >= 0 && focusTeam < 2 && focusPlayer >= 0 && focusPlayer < 11) {\n"
        "    average = GetTeam(focusTeam)->GetAllPlayers().at(focusPlayer)->GetPosition();\n"
        "  }",
    )
    replace(
        match.with_suffix(".cpp"), "\nvoid Match::UpdateCamera() {", "\nvoid Match::UpdateCamera() {"
    )  # Verify the companion API remains available.
    # Insert blending just before this function's closing brace.
    path = match.with_suffix(".cpp")
    text = path.read_text()
    start = text.index("void Match::UpdateIngameCamera(")
    next_function = text.index("\nvoid ", start + 10)
    closing = text.rfind("}", start, next_function)
    text = (
        text[:closing]
        + """
  if (method == 4 && focusTeam >= 0) {
    cameraOrientation.SetAngleAxis(0.45f * pi, Vector3(1, 0, 0));
    cameraNodeOrientation = QUATERNION_IDENTITY;
    cameraNodePosition = average + Vector3(0, -9.0f, 2.5f);
    cameraFOV = 35.0f;
    cameraNearCap = 1.0f;
  }
  cameraOrientation = previousOrientation.GetSlerped(blend, cameraOrientation);
  cameraNodeOrientation = previousNodeOrientation.GetSlerped(blend, cameraNodeOrientation);
  cameraNodePosition = previousPosition * (1.0f - blend) + cameraNodePosition * blend;
  cameraFOV = previousFOV * (1.0f - blend) + cameraFOV * blend;
"""
        + text[closing:]
    )
    path.write_text(text)
    ai = source / "ai.cpp"
    replace(
        ai,
        "#include <Python.h>",
        '#include <Python.h>\n#include "src/onthepitch/match.hpp"\n#include "src/onthepitch/team.hpp"\n#include "src/onthepitch/player/player.hpp"',
    )
    replace(
        ai,
        "  PyObject* get_frame_python() {",
        (Path(__file__).with_name("visual_bindings.cpp.inc")).read_text() + "\n  PyObject* get_frame_python() {",
    )
    replace(
        ai,
        '      .def("render", &GameEnv_Python::render_python)',
        '      .def("set_visual_player", &GameEnv_Python::visual_player_python)\n'
        '      .def("set_presentation_camera", &GameEnv_Python::camera_python)\n'
        '      .def("validate_presentation_animation", &GameEnv_Python::validate_animation_python)\n'
        '      .def("render_presentation_clip", &GameEnv_Python::render_clip_python)\n'
        '      .def("render", &GameEnv_Python::render_python)',
    )
    (root / "source_manifest.json").write_text(json.dumps({"original_source_sha256": hashes}, indent=2))
    build = root / "build"
    subprocess.run(["cmake", "-S", str(source), "-B", str(build)], check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", str(args.jobs)], check=True)
    shutil.copy2(build / "libgame.so", root / "_gameplayfootball.building.so")
    os.replace(root / "_gameplayfootball.building.so", root / "_gameplayfootball.so")
    print(f"Visual runtime ready: {root}")


if __name__ == "__main__":
    main()
