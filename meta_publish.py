#!/usr/bin/env python3
"""Publica/programa en Instagram (y Facebook Page) con la API oficial de Meta.

Variables de entorno (nunca pegues tokens en chats ni en archivos):
  META_ACCESS_TOKEN   (opcional) si el token va como Network secret no hace falta
  IG_USER_ID          (opcional) por defecto 'me' = la cuenta del token
  FB_PAGE_ID          (opcional) id de la página, solo para el comando fb-post
  META_GRAPH_VERSION  (opcional) por defecto v21.0

Por seguridad, TODO es simulación salvo que pases --confirm.
Solo usa la librería estándar de Python.
"""
import argparse, json, os, sys, time, urllib.parse, urllib.request, urllib.error
from datetime import datetime

ACCOUNT = None  # None = cuenta principal (Network secret)
GRAPH = "https://graph.instagram.com/" + os.environ.get("META_GRAPH_VERSION", "v21.0")


def env(name, required=True):
    v = os.environ.get(name)
    if required and not v:
        sys.exit(f"Falta la variable de entorno {name}")
    return v


def call(method, path, params):
    # Con un "Network secret" el entorno agrega Authorization: Bearer solo; sin él, usa META_ACCESS_TOKEN.
    tok = env("META_ACCESS_TOKEN", required=False)
    if ACCOUNT:  # cuentas extra: IG_TOKEN_2, IG_TOKEN_3...
        tok = env(f"IG_TOKEN_{ACCOUNT}")
    if tok:
        params = {**params, "access_token": tok}
    data = urllib.parse.urlencode(params).encode()
    url = f"{GRAPH}/{path}"
    req = urllib.request.Request(url + ("?" + data.decode() if method == "GET" else ""),
                                 data=None if method == "GET" else data, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Error de Meta {e.code}: {e.read().decode()}")


def ig_publish(a):
    """Crea el contenedor, espera a que procese y publica."""
    uid = env("IG_USER_ID", required=False) or "me"
    p = {"caption": a.caption or ""}
    if a.video_url:
        p.update(media_type="REELS", video_url=a.video_url)
    else:
        p["image_url"] = a.image_url
    if not a.confirm:
        print("[SIMULACIÓN] Se enviaría a Instagram:", json.dumps(p, ensure_ascii=False))
        print("Añade --confirm para publicar de verdad.")
        return
    cid = call("POST", f"{uid}/media", p)["id"]
    for _ in range(60):  # los videos pueden tardar
        st = call("GET", cid, {"fields": "status_code"}).get("status_code")
        if st == "FINISHED":
            break
        if st in ("ERROR", "EXPIRED"):
            sys.exit(f"El contenedor falló: {st}")
        time.sleep(5)
    print("Publicado:", call("POST", f"{uid}/media_publish", {"creation_id": cid}))


def ig_schedule(a):
    """Instagram NO tiene programación nativa en la API: se espera a la hora y se publica."""
    when = datetime.fromisoformat(a.at)
    wait = (when - datetime.now()).total_seconds()
    if wait <= 0:
        sys.exit("La hora ya pasó.")
    print(f"{'Esperando' if a.confirm else '[SIMULACIÓN] Esperaría'} {int(wait)} s hasta {when}.")
    print("Tip: mejor usa cron/'at' o una rutina de Claude que ejecute 'ig-post --confirm' a esa hora.")
    if a.confirm:
        time.sleep(wait)
    ig_publish(a)


def fb_post(a):
    """Facebook Page SÍ soporta programación nativa (10 min a 30 días en el futuro)."""
    pid = env("FB_PAGE_ID")
    p = {"message": a.message}
    if a.at:
        p.update(published="false", scheduled_publish_time=int(datetime.fromisoformat(a.at).timestamp()))
    if not a.confirm:
        print("[SIMULACIÓN] Se enviaría a Facebook:", json.dumps(p, ensure_ascii=False))
        return
    print(call("POST", f"{pid}/feed", p))


def check(a):
    print(call("GET", env("IG_USER_ID", required=False) or "me", {"fields": "username,media_count"}))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--account", help="número de cuenta extra (2 usa IG_TOKEN_2); sin esto, la cuenta principal")
    sub = ap.add_subparsers(required=True)
    c = sub.add_parser("check", help="verifica token y cuenta (solo lectura)"); c.set_defaults(f=check)
    for name, fn in (("ig-post", ig_publish), ("ig-schedule", ig_schedule)):
        s = sub.add_parser(name); s.set_defaults(f=fn)
        g = s.add_mutually_exclusive_group(required=True)
        g.add_argument("--image-url", help="URL pública de la imagen (JPEG)")
        g.add_argument("--video-url", help="URL pública del video (se publica como Reel)")
        s.add_argument("--caption")
        s.add_argument("--confirm", action="store_true")
        if name == "ig-schedule":
            s.add_argument("--at", required=True, help="ISO local, ej. 2026-10-21T18:00")
    f = sub.add_parser("fb-post"); f.set_defaults(f=fb_post)
    f.add_argument("--message", required=True); f.add_argument("--at"); f.add_argument("--confirm", action="store_true")
    a = ap.parse_args()
    global ACCOUNT
    ACCOUNT = a.account
    a.f(a)


if __name__ == "__main__":
    main()
