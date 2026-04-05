"""
10 logo candidates: THREE chibi pixel robots in a horizontal row (user-approved motif).
ComfyUI PixelArtDiffusionXL @ http://127.0.0.1:8188

Run: python generate_logo_robot_row_batch.py
Out: D:\\AI\\wangye\\assets\\logos-candidates\\row_logo_01.png ... 10.png
"""
from __future__ import annotations

import json
import shutil
import time
import uuid
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
CKPT = "SDXL1.0_PixelArtDiffusionXL_SpriteShaper.safetensors"
OUT_DIR = Path(r"D:\AI\wangye\assets\logos-candidates")
COMFY_OUT = Path(r"D:\AI\ComfyUI\output")

W = H = 640
STEPS = 28
CFG = 7.0

# Lock the visual DNA from the reference the user liked
BASE_POS = (
    "three cute chibi robot mascots standing in a neat horizontal row, equal spacing, same scale, "
    "large blocky rectangular heads with rounded corners, two small square antenna nubs on top of each head, "
    "big glowing square pixel eyes, simple horizontal line mouth, compact torso smaller than head, "
    "bright glowing square core light on each chest, short chunky block arms and legs, tiny oval shadow under each robot, "
    "pixel art 16-bit SNES style, crisp hard pixels, no anti-aliasing, centered composition, "
    "flat solid deep purple background, friendly AI agent team vibe, masterpiece game studio logo icon"
)

NEG = (
    "text, letters, words, watermark, signature, blurry, smooth gradient, photo realistic, 3d render, "
    "single robot, solo robot, two robots only, four robots, crowd, army, human face, human body, "
    "messy clutter, complex background, scenery, ground tiles, screenshot frame, ui chrome, jpeg artifacts, "
    "fused merged bodies, overlapping chaos, low resolution, ugly"
)

# Ten variations: color story + tiny flavor, still "three in a row" chibi bots
VARIATIONS = [
    "color story teal cyan and electric blue robots with warm yellow eye glow and amber chest cores, high contrast cute",
    "color story each robot different pastel lavender mint peach left to right, soft retro candy palette",
    "middle robot slightly taller leader pose hands on hips sidekicks mirror symmetric cute trio pixel",
    "tiny pixel neckties on all three robots office worker comedy cute same row business bots",
    "tiny yellow construction hard hats on three robots engineer squad cute pixel same lineup",
    "robots holding pixel hands together teamwork heartwarming same chibi proportions three in a row",
    "silhouette style dark bodies with hot pink cyan and yellow neon edge glow cyberpunk cute trio",
    "robots with small pixel headphones customer support theme cute three identical layout style",
    "robots jumping slight bounce mid-air cheerful same design family three characters row",
    "golden orange and coral robots with turquoise accents sunset arcade vibe three cute mascots row",
]


def build_workflow(prefix: str, width: int, height: int, pos: str, neg: str, seed: int) -> dict:
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": STEPS,
                "cfg": CFG,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
        },
        "4": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CKPT}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": width, "height": height, "batch_size": 1}},
        "6": {"class_type": "CLIPTextEncode", "inputs": {"text": pos, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"text": neg, "clip": ["4", 1]}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": prefix, "images": ["8", 0]}},
    }


def post(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.loads(r.read().decode())


def wait_done(prompt_id: str) -> dict:
    for i in range(300):
        time.sleep(1)
        h = json.loads(urllib.request.urlopen(f"{BASE}/history/{prompt_id}").read().decode())
        if prompt_id in h and h[prompt_id].get("outputs"):
            return h[prompt_id]["outputs"]
        if i % 25 == 0:
            print(f"    ...{i}s", flush=True)
    raise TimeoutError(prompt_id)


def copy_output(outputs: dict, dest: Path) -> None:
    for node in outputs.values():
        for im in node.get("images") or []:
            name = im.get("filename")
            if not name:
                continue
            sub = im.get("subfolder", "")
            src = COMFY_OUT / sub / name if sub else COMFY_OUT / name
            if src.is_file():
                shutil.copy2(src, dest)
                print(f"  -> {dest.name}", flush=True)
                return
    raise FileNotFoundError("no image in outputs")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    try:
        urllib.request.urlopen(f"{BASE}/system_stats", timeout=5).read()
    except OSError as e:
        raise SystemExit(f"ComfyUI not reachable at {BASE}: {e}") from e

    base_seed = int(time.time()) % (2**31)
    print(f"Generating 10 'three robots in a row' logos -> {OUT_DIR}\n", flush=True)

    for i, var in enumerate(VARIATIONS, start=1):
        prefix = f"row_logo_{i:02d}"
        dest = OUT_DIR / f"row_logo_{i:02d}.png"
        pos = f"{BASE_POS} {var}"
        seed = (base_seed + i * 9973) % (2**31)
        print(f"[{i:02d}/10] seed={seed}", flush=True)
        wf = build_workflow(prefix, W, H, pos, NEG, seed)
        cid = str(uuid.uuid4())
        r = post(f"{BASE}/prompt", {"prompt": wf, "client_id": cid})
        pid = r.get("prompt_id")
        if not pid:
            raise RuntimeError(r)
        outs = wait_done(pid)
        copy_output(outs, dest)

    print("\nDone. Open preview-row-robots.html in the same folder.", flush=True)


if __name__ == "__main__":
    main()
