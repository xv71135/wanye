"""Generate pixel-art UI assets via ComfyUI (PixelArtDiffusionXL). Run: python generate_pixel_ui_pack.py"""
import json
import shutil
import time
import uuid
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
CKPT = "SDXL1.0_PixelArtDiffusionXL_SpriteShaper.safetensors"
COMFY_OUT = Path(r"D:\AI\ComfyUI\output")
SITE_ASSETS = Path(r"D:\AI\wangye\assets")

JOBS = [
    {
        "dest": "pixel-hero-wide.png",
        "prefix": "pixel_ui_hero",
        "w": 1280,
        "h": 640,
        "pos": (
            "pixel art video game title screen background, retro sci-fi command deck, glowing cyan and "
            "magenta HUD frames, dark purple void with star dots, 16-bit SNES style, crisp hard pixels, "
            "no anti-aliasing, high contrast, dithering, tiny cute robot NPCs at corners, empty center "
            "for title text, masterpiece pixelart UI scene"
        ),
        "neg": (
            "blurry, smooth gradient, photo realistic, 3d render, vector, jpeg artifacts, text, watermark, "
            "anime face, messy composition"
        ),
    },
    {
        "dest": "pixel-ui-panel.png",
        "prefix": "pixel_ui_panel",
        "w": 768,
        "h": 512,
        "pos": (
            "pixel art RPG inventory menu panel texture, ornate golden frame on dark purple wood, "
            "retro game UI window, 16-bit, crisp pixels, symmetrical border, inner area flat for overlay text, "
            "SNES dialog box style, tileable feeling, masterpiece game UI art"
        ),
        "neg": (
            "blurry, photo, realistic, 3d, smooth, modern flat design, text, watermark, low resolution mess"
        ),
    },
    {
        "dest": "pixel-ui-cta.png",
        "prefix": "pixel_ui_cta",
        "w": 960,
        "h": 360,
        "pos": (
            "pixel art arcade neon marquee banner frame, hot pink and electric cyan glow, night cyberpunk "
            "pixel city silhouette border, empty center sign area for text, 16-bit arcade attract mode, "
            "crisp pixels, retro game over screen vibe, masterpiece UI"
        ),
        "neg": (
            "blurry, realistic photo, 3d render, vector, text letters, watermark, faces"
        ),
    },
]


def build_workflow(prefix: str, w: int, h: int, pos: str, neg: str, seed: int) -> dict:
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": 26,
                "cfg": 7.0,
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
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def run_job(job: dict, seed: int) -> None:
    wf = build_workflow(job["prefix"], job["w"], job["h"], job["pos"], job["neg"], seed)
    cid = str(uuid.uuid4())
    out = post(f"{BASE}/prompt", {"prompt": wf, "client_id": cid})
    pid = out["prompt_id"]
    src = None
    for _ in range(180):
        time.sleep(1)
        h = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}").read().decode())
        if pid not in h or not h[pid].get("outputs"):
            continue
        for node in h[pid]["outputs"].values():
            for im in node.get("images") or []:
                name = im.get("filename")
                if not name:
                    continue
                sub = im.get("subfolder", "")
                cand = COMFY_OUT / sub / name if sub else COMFY_OUT / name
                if cand.is_file():
                    src = cand
                    break
            if src:
                break
        if src:
            break
    else:
        raise TimeoutError(job["prefix"])

    dest = SITE_ASSETS / job["dest"]
    shutil.copy2(src, dest)
    print(f"OK {job['dest']} <- {src.name}", flush=True)


def main() -> None:
    SITE_ASSETS.mkdir(parents=True, exist_ok=True)
    base_seed = int(time.time()) % (2**31)
    for i, job in enumerate(JOBS):
        print(f"--- {job['dest']} ---", flush=True)
        run_job(job, (base_seed + i * 9973) % (2**31))
    print("All pixel UI assets copied to D:\\AI\\wangye\\assets\\", flush=True)


if __name__ == "__main__":
    main()
