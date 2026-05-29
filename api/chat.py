import orjson
import httpx
from fastapi import APIRouter, Request
from fastapi.responses import Response

import config

router = APIRouter()


def json_response(data: dict, status: int = 200) -> Response:
    return Response(
        content=orjson.dumps(data),
        status_code=status,
        media_type="application/json",
    )


def _build_system_prompt(search_data: dict) -> str:
    kataster = search_data.get("kataster", {})
    mets = search_data.get("mets")
    vaartus = search_data.get("vaartus")
    sinik = search_data.get("sinik")
    toetused = search_data.get("toetused", [])
    kitsendused = search_data.get("kitsendused", [])
    riskid = search_data.get("riskid", {})

    km = kataster.get("pindala_ha", 0)
    kataster_nr = kataster.get("number", "")
    omvorm = kataster.get("omvorm", "")
    aad = kataster.get("l_aadress", "")
    mk = kataster.get("mk_nimi", "")
    ov = kataster.get("ov_nimi", "")
    siht = kataster.get("sihtotstarve", "")

    er_text = "puudub"
    if mets:
        nr = mets.get("eraldise_nr", "?")
        pind = mets.get("pindala_ha", "?")
        bon = mets.get("boniteedi_kood", "?")
        vanus = mets.get("vanus", "?")
        tagavara = mets.get("tagavara_y_ha", 0)
        puuliik = mets.get("puuliik_kood", "?")
        raievanus = mets.get("raievanus", "?")
        er_text = f"Eraldis {nr} ({pind} ha), puuliik: {puuliik}, vanus: {vanus} a, boniteet: {bon}, tagavara: {tagavara} m³/ha, raievanus: {raievanus} a"

    v_text = "puudub"
    if vaartus:
        turu = vaartus.get("market_value", {})
        tulu = vaartus.get("income_value", {})
        valem = vaartus.get("formula_version", "§15")
        v_text = f"Valem: {valem}, turuhind: {turu.get('value', 0)} €, tuluhind: {tulu.get('value', 0)} €"

    s_text = "puudub"
    if sinik:
        co2 = sinik.get("total_co2_tons", 0)
        eur = sinik.get("value_eur", 0)
        s_text = f"CO₂: {co2:.1f} tonni, väärtus: {eur} €"

    sub_text = ""
    if toetused:
        for t in toetused:
            status = "✓ sobib" if t.get("status") == "eligible" else "✗ ei sobi"
            sub_text += f"\n  - {t.get('program', '')} ({t.get('amount', '')}): {status}. {t.get('reason', '')}"

    kits_text = ""
    if kitsendused:
        for k in kitsendused[:5]:
            kits_text += f"\n  - {k.get('tyyp', '')}: {k.get('kirjeldus', '')}"

    risk_text = ""
    if riskid:
        rv = riskid.get("raievanus", {})
        yr = riskid.get("yrask", {})
        risk_text = f"Raievanus: {rv.get('label', '?')}, Üürask: {yr.get('label', '?')}, Tervis: {riskid.get('terviseindeks', '?')}"

    return f"""Oled Terrapoint AI — Eesti metsanduse ja kinnisvara ekspert. Sa EI ole OWL ega muu mudel. Sa oled Terrapoint AI. Analüüsi antud katastriüksuse andmeid ja anna konkreetseid soovitusi. Vasta eesti keeles. Alusta lühikese tervitusega: "Tere! Terrapoint AI siin." Seejärel anna lühike kokkuvõte, kas tegu on metsamaaga või mitte, ning mis toetusi ja võimalusi on.

=== KATASTRIÜKSUS ===
Kataster: {kataster_nr}
Pindala: {km} ha
Aadress: {aad}, {ov}, {mk}
Sihtotstarve: {siht}
Omamise vorm: {omvorm}

=== METSAREGISTER ===
{er_text}

=== HINDAMINE ===
{v_text}

=== SÜSINIK ===
{s_text}

=== KAITSEALAD / PIIRANGUD ===
{kits_text if kits_text else "Piiranguid ei ole"}

=== RISKID ===
{risk_text if risk_text else "andmed puuduvad"}

=== TOETUSED ===
{sub_text if sub_text else "Toetusi ei leitud"}
"""


@router.post("/chat")
async def chat(request: Request, request_data: dict):
    kataster_nr = request_data.get("kataster_nr", "")
    message = request_data.get("message", "")
    history = request_data.get("history", [])

    if not kataster_nr or not message:
        return json_response({"error": "kataster_nr and message required"}, 400)

    # Call search endpoint internally
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            search_resp = await client.get(f"http://localhost:8000/api/search/{kataster_nr}")
            if search_resp.status_code == 404:
                return json_response({"error": "Katastri numbrit ei leitud"}, 404)
            if search_resp.status_code != 200:
                return json_response({"error": f"Otsingu viga: {search_resp.status_code}"}, 500)
            search_data = search_resp.json()
    except Exception as e:
        return json_response({"error": f"Otsingu viga: {str(e)}"}, 500)

    system_prompt = _build_system_prompt(search_data)

    messages = [{"role": "system", "content": system_prompt}]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": message})

    api_key = config.OPENROUTER_API_KEY
    if not api_key:
        return json_response({"error": "OpenRouter API key not configured"}, 500)

    api_url = "https://openrouter.ai/api/v1/chat/completions"
    model = config.OPENROUTER_MODEL or "openrouter/owl-alpha"

    try:
        async with httpx.AsyncClient(timeout=55) as client:
            resp = await client.post(
                api_url,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 800,
                },
            )
            if resp.status_code != 200:
                return json_response({"error": f"API viga: {resp.status_code}"}, 500)

            # Handle both JSON and SSE streaming responses
            content_type = resp.headers.get("content-type", "")
            if "text/event-stream" in content_type:
                full_text = ""
                for line in resp.text.split("\n"):
                    line = line.strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = orjson.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            full_text += delta.get("content", "")
                        except Exception:
                            continue
                if not full_text:
                    return json_response({"error": "AI ei vastanud"}, 500)
                return json_response({"content": full_text})
            else:
                try:
                    result = resp.json()
                except Exception:
                    return json_response({"error": "API vastus ei ole JSON"}, 500)
                choices = result.get("choices", [])
                if not choices:
                    error = result.get("error", {}).get("message", "Tühi vastus")
                    return json_response({"error": error}, 500)
                content = choices[0].get("message", {}).get("content", "")
                if not content:
                    return json_response({"error": "AI ei vastanud"}, 500)
                return json_response({"content": content})

    except httpx.TimeoutException:
        return json_response({"error": "AI vastus aegus (55s)"}, 504)
    except Exception as e:
        return json_response({"error": f"AI viga: {str(e)}"}, 500)
