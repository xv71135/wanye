"""Generate wide hero image via local ComfyUI /prompt. Run: python generate_hero_comfyui.py"""
import json
import shutil
import time
import uuid
import urllib.request
from pathlib import Path

BASE = "http://127.0.0.1:8188"
CKPT = "SDXL1.0_PixelArtDiffusionXL_SpriteShaper.safetensors"
WIDTH, HEIGHT = 1280, 640
OUT_PREFIX = "agentic_hero_apple_3d"

POS = (
    "premium minimalist wide hero banner, abstract 3D illustration, frosted glass spheres and soft "
    "brushed aluminum curves, apple.com keynote aesthetic, clean white and very light gray studio "
    "background, subtle sky blue rim light, soft diffused lighting, shallow depth of field, "
    "high-end product visualization, octane render look, symmetrical composition, generous negative "
    "space in center for headline text, no text, ultra sharp, 8k"
)
NEG = (
    "pixel art, 8-bit, sprite, video game screenshot, low resolution, text, watermark, logo, "
    "signature, blurry, noisy, deformed, people, faces, hands, cluttered, messy, dark, grim, "
    "cartoon, anime, ugly, amateur"
)

WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "seed": int(time.time()) % (2**31),
            "steps": 28,
            "cfg": 7.5,
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
    "5": {"class_type": "EmptyLatentImage", "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1}},
    "6": {"class_type": "CLIPTextEncode", "inputs": {"text": POS, "clip": ["4", 1]}},
    "7": {"class_type": "CLIPTextEncode", "inputs": {"text": NEG, "clip": ["4", 1]}},
    "8": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
    "9": {"class_type": "SaveImage", "inputs": {"filename_prefix": OUT_PREFIX, "images": ["8", 0]}},
}


def post(url: str, data: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())


def main() -> None:
    comfy_out = Path(r"D:\AI\ComfyUI\output")
    site_assets = Path(r"D:\AI\wangye\assets")
    site_assets.mkdir(parents=True, exist_ok=True)

    cid = str(uuid.uuid4())
    print("Queueing prompt...", flush=True)
    out = post(f"{BASE}/prompt", {"prompt": WORKFLOW, "client_id": cid})
    pid = out.get("prompt_id")
    if not pid:
        raise SystemExit(f"No prompt_id: {out}")

    for i in range(180):
        time.sleep(1)
        h = json.loads(urllib.request.urlopen(f"{BASE}/history/{pid}").read().decode())
        if pid in h and h[pid].get("outputs"):
            outputs = h[pid]["outputs"]
            print("Done:", json.dumps(outputs, indent=2)[:1200], flush=True)
            # Find first saved image path
            for node in outputs.values():
                imgs = node.get("images") or []
                for im in imgs:
                    name = im.get("filename")
                    sub = im.get("subfolder", "")
                    typ = im.get("type", "output")
                    if not name:
                        continue
                    src = comfy_out / sub / name if sub else comfy_out / name
                    if typ == "output" and src.is_file():
                        dest = site_assets / "hero-comfyui.png"
                        shutil.copy2(src, dest)
                        print(f"Copied to {dest}", flush=True)
                        return
            raise SystemExit("Outputs found but no image file path")
        if i % 15 == 0:
            print(f"  waiting... {i}s", flush=True)
    raise SystemExit("timeout waiting for ComfyUI")


if __name__ == "__main__":
    main()
