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
topics = ["mountain fog", "ocean waves", "forest mist", "night sky stars", "desert dunes", "storm clouds", "river nature", "sunrise clouds", "lake mountains", "waterfall"]
UA = {"User-Agent": "Mozilla/5.0"}
tmp = "/tmp/reel_work"; os.makedirs(tmp, exist_ok=True)
def get(u): return urllib.request.urlopen(urllib.request.Request(u, headers=UA)).read()
clips = []
for k in range(3):
    q = topics[((n - 1) * 3 + k) % len(topics)]
    url = "https://pixabay.com/api/videos/?" + urllib.parse.urlencode({"key": os.environ["PIXABAY_API_KEY"], "q": q, "per_page": 20, "min_width": 1280})
    hits = [h for h in json.loads(get(url))["hits"] if h["duration"] >= 6]
    h = random.choice(hits)
    v = h["videos"].get("large") or h["videos"]["medium"]
    p = f"{tmp}/c{k}.mp4"; open(p, "wb").write(get(v["url"])); clips.append(p)
# texto: una imagen por línea, con sombra
W, H = 1080, 1920
f = ImageFont.truetype(f"{D}/assets/Cinzel.ttf", 78); f.set_variation_by_axes([700])
fa = ImageFont.truetype(f"{D}/assets/Cinzel.ttf", 48); fa.set_variation_by_axes([500])
def layer(txt, font, fill, y):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    w = d.textlength(txt, font=font)
    for dx, dy, al in ((5, 5, 120), (3, 3, 220)):
        d.text(((W - w) / 2 + dx, y + dy), txt, font=font, fill=(0, 0, 0, al))
    d.text(((W - w) / 2, y), txt, font=font, fill=fill); return img
lines = textwrap.wrap(quote, 19)
lh = 108; y0 = (H - lh * len(lines)) // 2 - 70
layers = []  # (png, inicio, duración fade)
for j, ln in enumerate(lines):
    p = f"{tmp}/l{j}.png"; layer(ln, f, (246, 241, 229, 255), y0 + j * lh).save(p)
    layers.append((p, 0 if j == 0 else 0.5 + 0.55 * j, 0.01 if j == 0 else 0.7))
ya = y0 + lh * len(lines) + 40
line = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ImageDraw.Draw(line).rectangle([W // 2 - 70, ya, W // 2 + 70, ya + 3], fill=(214, 190, 130, 255))
line.save(f"{tmp}/gold.png")
layer("— " + author, fa, (222, 196, 135, 255), ya + 30).save(f"{tmp}/auth.png")
t_auth = 0.5 + 0.55 * len(lines) + 0.3
layers.append((f"{tmp}/gold.png", t_auth, 0.6)); layers.append((f"{tmp}/auth.png", t_auth + 0.3, 0.8))
DUR, CL, XF = 14.0, 5.6, 0.9
fc = []
for k in range(3):  # cada clip: encuadre vertical con deriva lenta + color cinematográfico
    fc.append(f"[{k}:v]trim=0:{CL},setpts=PTS-STARTPTS,fps=30,scale=1300:2312:force_original_aspect_ratio=increase,"
              f"crop=1080:1920:x='(iw-ow)/2+({ -30 if k % 2 else 30})*(t-2.8)':y='(ih-oh)/2+14*(t-2.8)',"
              f"eq=brightness=-0.26:contrast=1.12:saturation=0.85,colorbalance=rs=.05:bs=-.04,setsar=1[v{k}]")
fc.append(f"[v0][v1]xfade=transition=fade:duration={XF}:offset={CL - XF}[x1]")
fc.append(f"[x1][v2]xfade=transition=fade:duration={XF}:offset={2 * (CL - XF)}[x2]")
fc.append("[x2]vignette=PI/4.5,noise=alls=7:allf=t,format=yuv420p[base]")
last = "base"
for j, (p, st, fd) in enumerate(layers):
    idx = 3 + j
    fc.append(f"[{idx}:v]format=rgba" + (f",fade=t=in:st={st}:d={fd}:alpha=1" if st > 0 else "") + f"[t{j}]")
    fc.append(f"[{last}][t{j}]overlay=format=auto[o{j}]"); last = f"o{j}"
fc.append(f"[{last}]fade=t=out:st={DUR - 1}:d=1[vout]")
na = 3 + len(layers)
aud = ("aevalsrc='0.07*sin(2*PI*55*t)+0.05*sin(2*PI*110*t)+0.045*sin(2*PI*164.81*t+0.4*sin(2*PI*0.15*t))+0.04*sin(2*PI*196*t)+0.035*sin(2*PI*220.5*t)+0.03*sin(2*PI*329.6*t+0.3*sin(2*PI*0.23*t))"
       f"+0.10*sin(2*PI*48*t)*exp(-6*mod(t,2.4))':s=44100:d={DUR}")
fc.append(f"[{na}:a]lowpass=f=900,aecho=0.8:0.7:380|700:0.35|0.25,tremolo=f=0.18:d=0.35,afade=t=in:d=2,afade=t=out:st={DUR - 2.5}:d=2.5,volume=1.6[aout]")
cmd = ["ffmpeg", "-y", "-loglevel", "error"]
for c in clips: cmd += ["-i", c]
for p, _, _ in layers: cmd += ["-loop", "1", "-t", str(DUR), "-i", p]
cmd += ["-f", "lavfi", "-i", aud, "-filter_complex", ";".join(fc), "-map", "[vout]", "-map", "[aout]", "-t", str(DUR),
        "-c:v", "libx264", "-preset", "medium", "-crf", "25", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", f"{D}/reels/reel_{n:03d}.mp4"]
subprocess.run(cmd, check=True)
out = f"{D}/reels/reel_{n:03d}.mp4"
tags = "#estoicismo #filosofia #sabiduria #disciplina #mentalidad #reflexion #motivacion"
caption = f"“{quote}” — {author}\n\nGuarda esto para cuando lo necesites. 🏔️\n\n{tags}"
used.append(i); json.dump(used, open(U, "w"))
print(json.dumps({"file": out, "name": os.path.basename(out), "caption": caption, "author": author, "left": len(left) - 1}, ensure_ascii=False))
