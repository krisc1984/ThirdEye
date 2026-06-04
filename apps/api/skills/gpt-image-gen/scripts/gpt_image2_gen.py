#!/usr/bin/env python3
"""Generate images via GPT-Image-2 API and save as PNG files.

Usage:
    python scripts/gpt_image2_gen.py --prompt "a cat" --size "1024x1024" --n 1

Environment:
    GPT_IMAGE_API_KEY  - API key (required)
    GPT_IMAGE_API_URL  - API endpoint (optional, default: https://api.toplee.cn/v1/images/generations)
"""

import argparse
import base64
import json
import os
import sys
from datetime import datetime

import requests

DEFAULT_API_URL = "https://api.toplee.cn/v1/images/generations"


def generate(
    prompt, size="1024x1024", n=1, quality="high", model="gpt-image-2", seed=None
):
    api_key = os.environ.get("GPT_IMAGE_API_KEY")
    if not api_key:
        raise ValueError("Environment variable GPT_IMAGE_API_KEY is not set")
    api_url = os.environ.get("GPT_IMAGE_API_URL", DEFAULT_API_URL)

    payload = {
        "model": model,
        "prompt": prompt,
        "size": size,
        "response_format": "b64_json",
        "n": n,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    resp = requests.post(api_url, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Generate images via GPT-Image-2")
    parser.add_argument("--prompt", "-p", required=True, help="Image prompt")
    parser.add_argument(
        "--size",
        "-s",
        default="1024x1024",
        help="Image size (e.g. 1024x1024, 1792x1024)",
    )
    parser.add_argument("--n", type=int, default=1, help="Number of images")
    parser.add_argument(
        "--quality", "-q", default="high", choices=["high", "medium"], help="Quality"
    )
    parser.add_argument("--output-dir", "-o", default=".", help="Output directory")
    parser.add_argument(
        "--seed", type=int, default=None, help="Seed for reproducible generation"
    )
    args = parser.parse_args()

    print(f"Generating {args.n} image(s)...")
    print(f"  Prompt: {args.prompt}")
    print(f"  Size: {args.size}")
    print(f"  Quality: {args.quality}")

    result = generate(
        prompt=args.prompt,
        size=args.size,
        n=args.n,
        quality=args.quality,
        seed=args.seed,
    )

    if "data" not in result or len(result["data"]) == 0:
        print("No image data in response")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)
    saved = []
    for idx, item in enumerate(result["data"]):
        b64_data = item.get("b64_json", "")
        revised_prompt = item.get("revised_prompt", "")
        if not b64_data:
            continue
        image_data = base64.b64decode(b64_data)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gpt_image_{timestamp}_{idx}.png"
        filepath = os.path.join(args.output_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)
        saved.append(filepath)
        print(f"\n  Saved: {filepath} ({len(image_data) // 1024} KB)")
        if revised_prompt:
            print(f"  Revised prompt: {revised_prompt}")

    if not saved:
        print("No images were saved")
        sys.exit(1)

    return saved


if __name__ == "__main__":
    main()
