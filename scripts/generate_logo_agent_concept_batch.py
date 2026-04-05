"""
10 logos: same silhouette as user's reference (visor bots, single antenna, ear modules, 3 in a row, purple bg)
+ stronger "AI agent" metaphors (tools, graph links, orchestration, autonomy).

ComfyUI PixelArtDiffusionXL @ http://127.0.0.1:8188
Run: python generate_logo_agent_concept_batch.py
Out: D:\\AI\\wangye\\assets\\logos-candidates\\agent_logo_01.png ... 10.png
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
STEPS = 30
CFG = 7.2

# Visual DNA from the user's liked reference (no text in scene)
DNA = (
    "three identical chibi robot mascots in one horizontal row, same body scale and pose, "
    "large square head with rounded corners, big rectangular glowing visor as face screen, "
    "single slim antenna on top center of each head with bright glowing tip, "
    "round ear modules on both sides of each head, small metallic torso stubby arms and legs, "
    "subtle pixel shading cute 3d chibi, crisp SNES pixel art hard edges, "
    "flat vibrant purple background high contrast, centered iconic logo composition, masterpiece"
)

NEG = (
    "text, letters, numbers, words, typography, watermark, signature, logo text, "
    "blurry, smooth, photorealistic, 3d render octane, single robot, two robots, four robots, crowd, "
    "human face, human skin, messy background, scenery, floor tiles, screenshot frame, ui chrome, "
    "low quality, jpeg artifacts, fused bodies"
)

# Each line = "agent" concept layered on top of DNA
VARIATIONS = [
    "metaphor multi-agent: thin glowing pixel lines connect the three visors like a network graph nodes orchestration",
    "metaphor tool-using agents: left robot holds tiny pixel calculator middle holds wrench right holds pen stylus props very small",
    "metaphor autonomous loop: each chest has a small glowing square play-run icon suggesting task execution agent",
    "metaphor coordinator: middle robot visor brighter with subtle pixel wifi arc waves to left and right bots subservient agents",
    "metaphor LLM chat agents: visor glow shaped softer like rounded speech bubble screen still robotic cute",
    "metaphor knowledge RAG: tiny floating pixel document sheets and magnifying glass above the trio no text on sheets",
    "metaphor swarm: three small orbiting pixel cube satellites around the group suggesting tool plugins for agents",
    "metaphor pipeline: faint horizontal arrow flow of pixel particles passing through three bots left to right workflow",
    "metaphor safety guardrails: thin pixel hexagon shield outline behind trio transparent futuristic trust agent",
    "metaphor diverse roles same team: left bot white cyan visor middle silver hot pink visor right gold bronze purple visor like reference palette emphasis AI agent crew",
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
    print(f"Generating 10 agent-concept logos -> {OUT_DIR}\n", flush=True)

    for i, var in enumerate(VARIATIONS, start=1):
        prefix = f"agent_logo_{i:02d}"
        dest = OUT_DIR / f"agent_logo_{i:02d}.png"
        pos = f"{DNA} {var}"
        seed = (base_seed + i * 10007) % (2**31)
        print(f"[{i:02d}/10] seed={seed}", flush=True)
        wf = build_workflow(prefix, W, H, pos, NEG, seed)
        cid = str(uuid.uuid4())
        r = post(f"{BASE}/prompt", {"prompt": wf, "client_id": cid})
        pid = r.get("prompt_id")
        if not pid:
            raise RuntimeError(r)
        outs = wait_done(pid)
        copy_output(outs, dest)

    print("\nOpen logos-candidates/preview-agent-concepts.html", flush=True)


if __name__ == "__main__":
    main()
