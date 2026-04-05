"""
Optional ComfyUI batch: extra scenes in the SAME visual family as mascot-trio-official
(screen-face chibi bots, purple bg, headset sides, cute).

Outputs -> D:\\AI\\wangye\\assets\\mascot-extra\\ext_01.png ... ext_05.png

Run (ComfyUI on 8188):  python generate_mascot_extensions.py

Afterwards you can wire these into CSS or new sections (e.g. idle grey visor for "coming soon").
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
OUT_DIR = Path(r"D:\AI\wangye\assets\mascot-extra")
COMFY_OUT = Path(r"D:\AI\ComfyUI\output")

W = H = 640
STEPS = 28
CFG = 7.0

DNA = (
    "three cute chibi robots with large rounded helmets and rectangular glowing screen faces like old computer monitors, "
    "vertical pink rectangle eyes on screen, tiny mouth, side headset ear modules, small bodies, "
    "SNES pixel art crisp pixels, vibrant flat purple background, masterpiece cute mascot illustration"
)

NEG = (
    "text, letters, watermark, blurry, photorealistic, human, single robot only, two robots, four robots, "
    "messy background, low quality"
)

SCENES = [
    "wide shot trio standing proud slight bounce heroic pose sparkles above them celebration",
    "same trio sitting on ground tired cute grey dim screen faces idle loading state",
    "trio waving one hand each friendly welcome composition centered",
    "dramatic low angle trio looking slightly up epic but still cute pixel game poster",
    "trio holding one shared glowing wire between them teamwork data cable metaphor",
]


def build_workflow(prefix: str, w: int, h: int, pos: str, neg: str, seed: int) -> dict:
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
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": w, "height": h, "batch_size": 1}},
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
                return
    raise FileNotFoundError("no image")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    urllib.request.urlopen(f"{BASE}/system_stats", timeout=5).read()
    base_seed = int(time.time()) % (2**31)
    for i, scene in enumerate(SCENES, start=1):
        prefix = f"mascot_ext_{i:02d}"
        dest = OUT_DIR / f"ext_{i:02d}.png"
        pos = f"{DNA} {scene}"
        seed = (base_seed + i * 8191) % (2**31)
        print(f"[{i}/5] {dest.name} seed={seed}", flush=True)
        wf = build_workflow(prefix, W, H, pos, NEG, seed)
        r = post(f"{BASE}/prompt", {"prompt": wf, "client_id": str(uuid.uuid4())})
        pid = r["prompt_id"]
        outs = wait_done(pid)
        copy_output(outs, dest)
        print("  ok", flush=True)
    print("Done ->", OUT_DIR)


if __name__ == "__main__":
    main()
