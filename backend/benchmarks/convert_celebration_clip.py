"""Prototype: retarget CC0 glTF Cheer rotations into GRF's .anim rig.

Exports an isolated presentation asset, never installs it into the authoritative
animation collection (whose ordering is part of existing state archives).
"""

import argparse
import hashlib
import json
import struct
from pathlib import Path
import numpy as np

RIG = {
    "body": ("hips", None),
    "middle": ("chest", "body"),
    "neck": ("head", "middle"),
    "left_shoulder": ("upperarm.l", "middle"),
    "left_elbow": ("lowerarm.l", "left_shoulder"),
    "right_shoulder": ("upperarm.r", "middle"),
    "right_elbow": ("lowerarm.r", "right_shoulder"),
    "left_thigh": ("upperleg.l", "body"),
    "left_knee": ("lowerleg.l", "left_thigh"),
    "left_ankle": ("foot.l", "left_knee"),
    "right_thigh": ("upperleg.r", "body"),
    "right_knee": ("lowerleg.r", "right_thigh"),
    "right_ankle": ("foot.r", "right_knee"),
}
VERIFIED_CC0_SHA256 = "60428e3abc09ba83e595d256e3af8c5c976b46cdae599f0802fc82b4a3445168"


def unit(q):
    q = np.asarray(q, dtype=float)
    return q / np.linalg.norm(q)


def inverse(q):
    return np.array([-q[0], -q[1], -q[2], q[3]])


def multiply(a, b):
    xyz = a[3] * b[:3] + b[3] * a[:3] + np.cross(a[:3], b[:3])
    return unit(np.r_[xyz, a[3] * b[3] - np.dot(a[:3], b[:3])])


def slerp(a, b, t):
    a, b = unit(a), unit(b)
    dot = np.dot(a, b)
    if dot < 0:
        b = -b
        dot = -dot
    if dot > 0.9995:
        return unit(a + (b - a) * t)
    angle = np.arccos(np.clip(dot, -1, 1))
    return unit((a * np.sin((1 - t) * angle) + b * np.sin(t * angle)) / np.sin(angle))


def convert(source, template, output):
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != VERIFIED_CC0_SHA256:
        raise ValueError("Source differs from the verified official CC0 KayKit asset")
    magic, version, length = struct.unpack_from("<III", raw)
    if magic != 0x46546C67 or version != 2 or length != len(raw):
        raise ValueError("Invalid GLB")
    json_size, json_type = struct.unpack_from("<II", raw, 12)
    doc = json.loads(raw[20 : 20 + json_size])
    binary_offset = 20 + json_size
    binary_size, binary_type = struct.unpack_from("<II", raw, binary_offset)
    if json_type != 0x4E4F534A or binary_type != 0x004E4942:
        raise ValueError("Unsupported GLB chunks")
    binary = raw[binary_offset + 8 : binary_offset + 8 + binary_size]

    def accessor(index):
        a = doc["accessors"][index]
        v = doc["bufferViews"][a["bufferView"]]
        if a["componentType"] != 5126 or a.get("sparse"):
            raise ValueError("Only dense float animation accessors are supported")
        components = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[a["type"]]
        start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = v.get("byteStride", components * 4)
        return np.ndarray(
            (a["count"], components), dtype="<f4", buffer=binary, offset=start, strides=(stride, 4)
        ).copy()

    animation = next(a for a in doc["animations"] if a["name"] == "Cheer")
    channels = {}
    duration = 0
    for channel in animation["channels"]:
        sampler = animation["samplers"][channel["sampler"]]
        if sampler.get("interpolation", "LINEAR") != "LINEAR":
            raise ValueError("Unsupported interpolation")
        times = accessor(sampler["input"])[:, 0]
        duration = max(duration, float(times[-1]))
        if channel["target"]["path"] == "rotation":
            channels[channel["target"]["node"]] = (times, accessor(sampler["output"]))
    nodes = doc["nodes"]
    names = {n["name"]: i for i, n in enumerate(nodes) if n.get("name")}
    parents = {child: i for i, n in enumerate(nodes) for child in n.get("children", [])}

    def source_globals(time=None):
        result = {}

        def rotation(i):
            if i in result:
                return result[i]
            q = unit(nodes[i].get("rotation", [0, 0, 0, 1]))
            if time is not None and i in channels:
                times, values = channels[i]
                high = int(np.searchsorted(times, time))
                high = min(max(high, 1), len(times) - 1)
                low = high - 1
                t = np.clip((time - times[low]) / max(times[high] - times[low], 1e-9), 0, 1)
                q = slerp(values[low], values[high], t)
            result[i] = multiply(rotation(parents[i]), q) if i in parents else q
            return result[i]

        for i in range(len(nodes)):
            rotation(i)
        return result

    native_bind = {}
    for line in template.read_text().splitlines():
        parts = line.split(",")
        if parts[0] in RIG:
            native_bind[parts[0]] = unit([float(v) for v in parts[2:6]])
    if set(native_bind) != set(RIG):
        raise ValueError("Native template does not cover the mapped rig")
    native_globals = {}
    for target, (_, parent) in RIG.items():
        native_globals[target] = (
            multiply(native_globals[parent], native_bind[target]) if parent else native_bind[target]
        )
    source_bind = source_globals()
    basis = unit([np.sin(np.pi / 4), 0, 0, np.cos(np.pi / 4)])  # glTF Y-up -> native Z-up
    tracks = {k: [k] for k in RIG}
    frame_count = round(duration * 100)
    for frame in range(frame_count + 1):
        globals_now = source_globals(frame / 100)
        desired = {}
        for target, (name, parent) in RIG.items():
            i = names[name]
            delta = multiply(globals_now[i], inverse(source_bind[i]))
            converted = multiply(multiply(basis, delta), inverse(basis))
            desired[target] = multiply(converted, native_globals[target])
            local = multiply(inverse(desired[parent]), desired[target]) if parent else desired[target]
            tracks[target].extend([str(frame), *(f"{v:.7f}" for v in local)])
    output.parent.mkdir(parents=True, exist_ok=True)
    root = f"player,0,0,0,-0.07,{frame_count},0,0,-0.07"
    output.write_text(
        root
        + "\n"
        + "\n".join(",".join(row) for row in tracks.values())
        + "\n<specialvar1>1</specialvar1>\n<specialvar2>1</specialvar2>\n<type>special</type>\n"
    )
    report = {
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "clip": "Cheer",
        "source_license": "CC0-1.0",
        "duration_seconds": duration,
        "native_frames": frame_count + 1,
        "bones": list(RIG),
        "root_motion": "pinned",
        "status": "isolated retargeting prototype; not registered in simulation animation collection",
    }
    output.with_suffix(".conversion.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("template", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(convert(args.source, args.template, args.output), indent=2))


if __name__ == "__main__":
    main()
