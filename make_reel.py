#!/usr/bin/env python3
"""Genera el siguiente reel estoico para nodx301. Uso: make_reel.py  -> imprime ruta del mp4, caption y nombre en JSON.
Requiere PIXABAY_API_KEY, ffmpeg, Pillow. Estado en used.json."""
import json, os, random, subprocess, sys, textwrap, urllib.request, urllib.parse
from PIL import Image, ImageDraw, ImageFont
D = os.path.dirname(os.path.abspath(__file__))
Q = json.load(open(f"{D}/quotes.json", encoding="utf-8"))
U = f"{D}/used.json"
used = json.load(open(U)) if os.path.exists(U) else []
left = [i for i in range(len(Q)) if i not in used]
if not left:
    sys.exit("SIN_FRASES: agrega frases nuevas a quotes.json")
i = left[0]; quote, author = Q[i]
n = len(used) + 1
topics = ["mountain fog", "ocean waves", "forest mist", "night sky stars", "desert dunes", "storm clouds", "river nature", "sunrise clouds"]
q = topics[(n - 1) % len(topics)]
url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": os.environ["PIXABAY_API_KEY"], "q": q, "per_page": 20, "min_width": 1280})
hits = [h for h in json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})))["hits"] if h["duration"] >= 10]
h = random.choice(hits)
v = h["videos"].get("large") or h["videos"]["medium"]
tmp = "/tmp/reel_work"; os.makedirs(tmp, exist_ok=True)
src = f"{tmp}/src.mp4"; open(src, "wb").write(urllib.request.urlopen(urllib.request.Request(v["url"], headers={"User-Agent": "Mozilla/5.0"})).read())
# texto
W, H = 1080, 1920
img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
f = ImageFont.truetype(f"{D}/assets/Cinzel.ttf", 74); f.set_variation_by_axes([700])
fa = ImageFont.truetype(f"{D}/assets/Cinzel.ttf", 46); fa.set_variation_by_axes([500])
lines = textwrap.wrap(quote, 20)
lh = 100; y = (H - lh * len(lines)) // 2 - 60
for ln in lines:
    w = d.textlength(ln, font=f)
    d.text(((W - w) / 2 + 3, y + 3), ln, font=f, fill=(0, 0, 0, 200))
    d.text(((W - w) / 2, y), ln, font=f, fill=(245, 240, 228, 255)); y += lh
a = "— " + author; w = d.textlength(a, font=fa)
d.text(((W - w) / 2, y + 50), a, font=fa, fill=(214, 190, 130, 255))
img.save(f"{tmp}/text.png")
out = f"{D}/reels/reel_{n:03d}.mp4"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-stream_loop", "-1", "-i", src, "-i", f"{tmp}/text.png",
  "-f", "lavfi", "-i", "aevalsrc='0.10*sin(2*PI*110*t)+0.07*sin(2*PI*164.8*t)+0.05*sin(2*PI*220*t+0.5*sin(2*PI*0.2*t))':s=44100:d=12",
  "-filter_complex", "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=brightness=-0.28:saturation=0.8,fps=30[b];[b][1:v]overlay[v];[2:a]lowpass=f=600,afade=t=in:d=1.5,afade=t=out:st=10.5:d=1.5[a]",
  "-map", "[v]", "-map", "[a]", "-t", "12", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out], check=True)
tags = "#estoicismo #filosofia #sabiduria #disciplina #mentalidad #reflexion #motivacion"
caption = f"“{quote}” — {author}\n\nGuarda esto para cuando lo necesites. 🏔️\n\n{tags}"
used.append(i); json.dump(used, open(U, "w"))
print(json.dumps({"file": out, "name": os.path.basename(out), "caption": caption, "author": author, "left": len(left) - 1}, ensure_ascii=False))
