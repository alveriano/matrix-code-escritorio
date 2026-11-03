#!/usr/bin/env python3
"""Busca os números do canal do CowTalk no YouTube (YouTube Data API v3) e grava no Supabase.

Roda no GitHub Actions logo depois do robô do Instagram. Precisa de dois segredos do repositório:
  YOUTUBE_API_KEY  chave de API do Google Cloud com a YouTube Data API v3 ligada
  IG_TOKEN         o mesmo token do Instagram, que deixa gravar pela função ig_gravar
Gasta uns 10 pontos da cota de 10.000 por dia a cada rodada (cerca de 2.900 por dia).
Não imprime números nem segredos: o log deste repositório é público.
"""
import datetime, json, os, sys, urllib.error, urllib.parse, urllib.request

CANAL = "UCgPXhigMf1bGLcfkWEcb72A"  # youtube.com/@PodcastCowtalk
SUPABASE = "https://ekkxiwasmwhhotblbvpi.supabase.co/rest/v1/rpc/ig_gravar"
CHAVE_PUBLICA = "sb_publishable_kCjF76j4D6gfVlE3ixjwAg_fwFRJohb"


def youtube_pagina(recurso, **params):
    q = urllib.parse.urlencode({"key": os.environ["YOUTUBE_API_KEY"].strip(), **params})
    with urllib.request.urlopen(f"https://www.googleapis.com/youtube/v3/{recurso}?{q}", timeout=60) as r:
        return json.load(r)


def youtube(recurso, **params):
    return youtube_pagina(recurso, **params).get("items", [])


def gravar(nome, linhas):
    corpo = json.dumps({"token": os.environ["IG_TOKEN"], "chave_": nome, "dados_": linhas}).encode()
    req = urllib.request.Request(SUPABASE, data=corpo, headers={"apikey": CHAVE_PUBLICA, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()


def numero(d, k):
    return int(d[k]) if k in d else None


if not os.environ.get("YOUTUBE_API_KEY", "").strip():
    print("youtube: sem YOUTUBE_API_KEY, pulando")
    sys.exit(0)

try:
    canal = youtube("channels", part="snippet,statistics,contentDetails", id=CANAL)[0]
    st = canal["statistics"]
    hoje = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=-3))).date().isoformat()
    resumo = {"titulo": canal["snippet"]["title"], "inscritos": None if st.get("hiddenSubscriberCount") else numero(st, "subscriberCount"),
              "views": numero(st, "viewCount"), "videos": numero(st, "videoCount")}
    uploads = canal["contentDetails"]["relatedPlaylists"]["uploads"]
    ids, pagina = [], None
    while len(ids) < 1000:  # todos os vídeos do canal, 50 por página
        r = youtube_pagina("playlistItems", part="contentDetails", playlistId=uploads, maxResults=50, **({"pageToken": pagina} if pagina else {}))
        ids += [i["contentDetails"]["videoId"] for i in r.get("items", [])]
        pagina = r.get("nextPageToken")
        if not pagina:
            break
    itens = [v for k in range(0, len(ids), 50) for v in youtube("videos", part="snippet,statistics,contentDetails", id=",".join(ids[k:k + 50]))]
    videos = []
    for v in itens:
        s = v.get("statistics", {})
        videos.append({"id": v["id"], "titulo": v["snippet"]["title"][:120], "date": v["snippet"]["publishedAt"][:10],
                       "duracao": v["contentDetails"].get("duration"), "views": numero(s, "viewCount"),
                       "likes": numero(s, "likeCount"), "comments": numero(s, "commentCount")})
    gravar("yt_canal", [resumo])
    gravar("yt_videos", videos)
    gravar("yt_hist", [{"date": hoje, "inscritos": resumo["inscritos"], "views": resumo["views"], "videos": resumo["videos"]}])
    print(f"youtube: canal e {len(videos)} vídeos gravados")
except urllib.error.HTTPError as e:
    msg = e.read()[:300].decode(errors="replace")
    for segredo in (os.environ["YOUTUBE_API_KEY"].strip(), os.environ.get("IG_TOKEN", "")):
        if segredo:
            msg = msg.replace(segredo, "***")
    print(f"youtube: erro HTTP {e.code} em {e.url.split('?')[0]}: {msg}")
    sys.exit(1)
except Exception as e:
    print(f"youtube: falhou ({type(e).__name__})")
    sys.exit(1)
