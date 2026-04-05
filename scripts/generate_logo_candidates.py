"""
Generate 10 pixel-art logo candidates via local ComfyUI (PixelArtDiffusionXL).
Requires ComfyUI on http://127.0.0.1:8188

Run: python generate_logo_candidates.py
Outputs: D:\\AI\\wangye\\assets\\logos-candidates\\logo_candidate_01.png ... 10.png
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

# Square icons — readable at favicon / nav size when downscaled
W = H = 640
STEPS = 28
CFG = 7.0

NEG = (
    "text, letters, words, watermark, signature, blurry, smooth gradient, photo realistic, "
    "3d render, messy background, cluttered, multiple characters, ugly, low quality, jpeg artifacts, "
    "frame border screenshot, ui chrome"
)

# Ten distinct directions: one glance = one idea (AI / lab / agents / tech)
PROMPTS = [
    "single cute robot head mascot logo, symmetrical front view, big eyes, antenna, pixel art game studio icon, "
    "dark purple background, cyan and hot pink accent highlights, ultra simple silhouette, centered, masterpiece pixel logo",

    "abstract AI brain made of glowing square nodes and connection lines, round emblem, pixel art icon, "
    "minimal, dark violet void background, teal glow, iconic tech symbol, centered, crisp pixels",

    "one glowing sphere core with two orbiting pixel rings, sci-fi AI nucleus logo, pixel art, "
    "high contrast, purple and electric blue, simple cosmic icon, centered, no clutter",

    "retro science lab flask with single lightning bolt inside, pixel art logo mark, "
    "golden and cyan glass glow, dark background, friendly mad-scientist vibe, centered emblem",

    "three small agent bots holding hands in triangle formation, cute pixel art team logo, "
    "minimal characters, soft pastel on dark purple, memorable cooperative symbol, centered",

    "shield shape with microchip circuit pattern inside, cybersecurity AI emblem, pixel art, "
    "silver and cyan, bold readable silhouette, game guild icon style, centered",

    "interlocking gear and single spark star, automation agent logo, pixel art industrial cute, "
    "orange and teal accent, dark background, simple mechanical icon, centered",

    "stylized neural network diamond: four nodes one center link, abstract agent mesh logo, pixel art, "
    "magenta and mint green, geometric minimal, iconic, centered",

    "pixel art friendly ghost-wizard hat combined with cpu chip, playful AI familiar mascot, "
    "one character only, purple robe cyan eyes, dark starfield bg, centered cute logo",

    "minimal rocket launching from open book pages, knowledge agents logo, pixel art, "
    "yellow flame teal book, dark purple sky, aspirational simple icon, centered masterpiece",
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
        if i % 20 == 0:
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
                print(f"  saved {dest.name}", flush=True)
                return
    raise FileNotFoundError("no image in outputs")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base_seed = int(time.time()) % (2**31)

    # Health check
    try:
        urllib.request.urlopen(f"{BASE}/system_stats", timeout=5).read()
    except OSError as e:
        raise SystemExit(f"ComfyUI not reachable at {BASE}: {e}") from e

    print(f"Generating {len(PROMPTS)} logo candidates -> {OUT_DIR}\n", flush=True)

    for i, pos in enumerate(PROMPTS, start=1):
        prefix = f"agentic_logo_cand_{i:02d}"
        dest = OUT_DIR / f"logo_candidate_{i:02d}.png"
        seed = (base_seed + i * 7919) % (2**31)
        print(f"[{i:02d}/10] {prefix} seed={seed}", flush=True)
        wf = build_workflow(prefix, W, H, pos, NEG, seed)
        cid = str(uuid.uuid4())
        r = post(f"{BASE}/prompt", {"prompt": wf, "client_id": cid})
        pid = r.get("prompt_id")
        if not pid:
            raise RuntimeError(r)
        outs = wait_done(pid)
        copy_output(outs, dest)

    print("\nDone. Review PNGs in:", OUT_DIR, flush=True)
    print("Pick one, then copy to assets/logo.png and wire <link rel=icon> in HTML.", flush=True)


if __name__ == "__main__":
    main()
