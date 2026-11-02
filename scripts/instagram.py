#!/usr/bin/env python3
"""Busca os números do Instagram do CowTalk no Windsor.ai e grava no Supabase.

Roda no GitHub Actions a cada 15 minutos. Precisa de dois segredos do repositório:
  WINDSOR_API_KEY  chave de API do Windsor.ai
  IG_TOKEN         token que deixa gravar na tabela public.instagram (função ig_gravar)
Não imprime números nem segredos: o log deste repositório é público.
"""
import json, os, sys, urllib.error, urllib.parse, urllib.request

SUPABASE = "https://ekkxiwasmwhhotblbvpi.supabase.co/rest/v1/rpc/ig_gravar"
CHAVE_PUBLICA = "sb_publishable_kCjF76j4D6gfVlE3ixjwAg_fwFRJohb"
CONSULTAS = {
    "perfil": {"fields": "username,followers_count,media_count"},
    "dias": {"fields": "date,reach,views,accounts_engaged,total_interactions,likes,comments,shares,saves", "date_preset": "last_180dT"},
    "seg": {"fields": "date,follower_count_1d", "date_preset": "last_30d"},
    "posts": {"fields": "date,media_type,media_caption,media_permalink,media_views,media_shares,media_saved", "date_preset": "last_30d"},
}


def chave_windsor():
    chave = os.environ["WINDSOR_API_KEY"].strip()
    if "api_key=" in chave:  # aceita o endereço inteiro copiado do Data Preview do Windsor
        chave = urllib.parse.parse_qs(urllib.parse.urlsplit(chave).query).get("api_key", [""])[0]
    return chave


def windsor(consulta):
    q = urllib.parse.urlencode({"api_key": chave_windsor(), **consulta})
    with urllib.request.urlopen("https://connectors.windsor.ai/instagram?" + q, timeout=120) as r:
        corpo = json.load(r)
    linhas = corpo.get("data", corpo) if isinstance(corpo, dict) else corpo
    if not isinstance(linhas, list):
        raise ValueError("resposta do Windsor sem lista de dados")
    return linhas


def enxugar(nome, linhas):
    if nome == "posts":
        for r in linhas:  # só a primeira linha da legenda, para caber e carregar rápido
            cap = next((l for l in (r.get("media_caption") or "").splitlines() if l.strip()), "")
            r["media_caption"] = cap[:200]
    return linhas


def gravar(nome, linhas):
    corpo = json.dumps({"token": os.environ["IG_TOKEN"], "chave_": nome, "dados_": linhas}).encode()
    req = urllib.request.Request(SUPABASE, data=corpo, headers={"apikey": CHAVE_PUBLICA, "Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=60).read()


falhas = 0
for nome, consulta in CONSULTAS.items():
    try:
        linhas = enxugar(nome, windsor(consulta))
        gravar(nome, linhas)
        print(f"{nome}: {len(linhas)} linhas gravadas")
    except urllib.error.HTTPError as e:
        falhas += 1
        print(f"{nome}: erro HTTP {e.code} em {e.url.split('?')[0]}")
    except Exception as e:
        falhas += 1
        print(f"{nome}: falhou ({type(e).__name__})")
sys.exit(1 if falhas == len(CONSULTAS) else 0)
