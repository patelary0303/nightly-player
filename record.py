"""Record episodes to MP3 with Kokoro.

Usage: python record.py <episodes dir> <audio dir> [keep]

Each episodes/<id>.json is {"id", "title", "date", "hosts", "chapters",
"turns": [{"speaker": "A" | "B", "text": "..."}]}. For every episode whose
audio is missing or was made from a different script, this writes
<audio dir>/<id>.mp3 and <id>.times.json ({"sha", "starts", "duration"}, where
starts[i] is the second turn i begins). Then only the newest `keep` episodes
(default 14) are left in <audio dir>. Voices and pacing match index.html.
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

import numpy as np

RATE = 24000
GAP_SEC = 0.3
VOICES = {"A": "af_heart", "B": "am_puck"}
SPEED = {"A": 1.0, "B": 1.08}


def render(pipeline, turns):
    pieces, starts, t = [], [], 0.0
    gap = np.zeros(int(RATE * GAP_SEC), dtype=np.float32)
    for turn in turns:
        starts.append(round(t, 2))
        who = turn["speaker"]
        for _, _, audio in pipeline(turn["text"], voice=VOICES.get(who, VOICES["A"]), speed=SPEED.get(who, 1.0)):
            a = np.asarray(audio.numpy() if hasattr(audio, "numpy") else audio, dtype=np.float32)
            pieces.append(a)
            t += len(a) / RATE
        pieces.append(gap)
        t += GAP_SEC
    return np.concatenate(pieces), starts, round(t, 2)


def to_mp3(samples, path):
    pcm = (np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "-i", "-",
         "-codec:a", "libmp3lame", "-b:a", "64k", path],
        input=pcm, check=True,
    )


def main():
    src, out = sys.argv[1], sys.argv[2]
    keep = int(sys.argv[3]) if len(sys.argv) > 3 else 14
    os.makedirs(out, exist_ok=True)
    pipeline = None
    for path in sorted(glob.glob(os.path.join(src, "*.json"))):
        with open(path, encoding="utf-8") as f:
            raw = f.read()
        ep = json.loads(raw)
        ep_id = ep.get("id") or os.path.splitext(os.path.basename(path))[0]
        sha = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
        times_path = os.path.join(out, f"{ep_id}.times.json")
        if os.path.exists(times_path):
            with open(times_path, encoding="utf-8") as f:
                if json.load(f).get("sha") == sha:
                    continue
        if pipeline is None:
            from kokoro import KPipeline
            pipeline = KPipeline(lang_code="a")
        turns = [t for t in ep["turns"] if t.get("text", "").strip()]
        samples, starts, duration = render(pipeline, turns)
        to_mp3(samples, os.path.join(out, f"{ep_id}.mp3"))
        with open(times_path, "w", encoding="utf-8") as f:
            json.dump({"sha": sha, "starts": starts, "duration": duration}, f)
        print(f"recorded {ep_id}: {len(turns)} turns, {duration / 60:.1f} min")

    ids = sorted({os.path.basename(p).split(".")[0] for p in glob.glob(os.path.join(out, "*.times.json"))})
    for old in ids[:-keep] if len(ids) > keep else []:
        for ext in (".mp3", ".times.json"):
            p = os.path.join(out, old + ext)
            if os.path.exists(p):
                os.remove(p)
        print(f"pruned {old}")


if __name__ == "__main__":
    main()
