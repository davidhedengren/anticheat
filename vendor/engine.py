#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI STYLE TRIAGE v2.10
====================

Ett förklarbart screeningsverktyg för stilistiska signaler som ibland kan
samvariera med AI-assisterat skrivande.

VIKTIGT:
- Programmet bevisar inte att AI har använts.
- Det fastställer inte författarskap.
- Det ska användas som ett jämförelse- och reflektionsverktyg.
- Starkast användning: jämför en aktuell text med tidigare texter av samma skribent.

NYTT I v2.10
-----------
1. Förbättrad analys av samordningar med "och/eller" respektive "and/or":
   programmet försöker extrahera HELA samordnade fraser, inte bara närmaste ord.
   Exempel:
       "utstötta barn och omtyckta barn"
   blir ungefär:
       vänster = "utstötta barn"
       höger   = "omtyckta barn"

2. Treled:
       "språkliga, kroppsliga och symboliska uttryck"
   kan identifieras som en A, B och C-struktur.

3. Sonifiering är inbyggd:
   samma indikatorer som syns i rapporten kan också höras som en WAV-fil.

4. Version 2.1 skiljer mellan strukturerade fraslistor och vanligt satsbindande
   "och". Satskopplingar är i första hand en motvikt och skapar inte längre ett
   fullt ljudslag. Upprepningar av exakt samma fraspar tonas dessutom ned.

5. Version 2.2 behåller analysen men ger signalerna en generisk
   flipper-/tivolikaraktär och använder 80 procent händelsekadens.

6. Version 2.3 skilde på meningspunkt och analysresultat.

7. Version 2.4 gör ljudklassningen av "och/eller" mer konservativ:
   - tydliga nominala fraspar får låg–hög-flipperljud;
   - sats- och verbfraskopplingar är tysta;
   - osäkra fall är också tysta.
   Denna extra trevägsfiltrering påverkar sonifieringen men lämnar det
   kalibrerade analysindexet oförändrat.

8. Version 2.4 ersatte meningspunkterna med en jämn tidsmarkör.

9. Version 2.5 band tidsmarkören direkt till textmängden.

10. Version 2.6 ökade uppspelningshastigheten till 0,25 sekund per tick.

11. Version 2.7 ökar hastigheten ytterligare:
   - ett tick spelas fortfarande efter varje 30 ord;
   - texttidslinjen löper med 200 ord per sekund;
   - tickintervallet blir därför 0,15 sekund;
   - ljudfilens längd bestäms av textens ordantal och är inte längre fixerad.
   Alla analysljud använder samma ordskala, så deras avstånd till tickljuden
   visar var de uppträder i textflödet.

12. Version 2.8 delar ljudpaletten i två tydliga familjer:
   - enskilda fraspar, treled och kontrastmallar är korta melodiska figurer;
   - lokal täthet markeras med ett lågt mekaniskt dubbellarm;
   - extrem täthet markeras med ett långt sammanhängande wow-svep och brusfinal.
   Täthetsljuden återanvänder inte flipperklockorna från grundsignalerna.

13. Version 2.9 skiljer uttryckligen mellan rå användning av "och" och
    "eller" och använder meningskontext i ljudfiltret:
   - meningsinledande "och" är tyst;
   - meningar med minst fem "och" behandlas som satskedjor och är tysta;
   - vanliga fraspar i meningar över 20 ord med minst tre "och" är tysta,
     medan ett tydligt treled fortfarande kan höras;
   - lokal täthet ger större bidrag för säkra treled än för vanliga par och
     dämpas av satslik samordning. Reglerna påverkar ljudbilden, inte det
     sedan tidigare kalibrerade avvikelseindexet.

14. Version 2.10 låter wow-svepet återkomma vid fler starka strukturkluster:
    wow-tröskeln sänks från 6,0 till 5,5, medan spärren på 180 ord och kravet
    på globalt avvikelseindex minst 0,50 behålls.

Kommandon:
    python ai_style_triage_v2_10.py analyze text.txt --lang sv
    python ai_style_triage_v2_10.py analyze text.txt --lang sv --json report.json --csv features.csv
    python ai_style_triage_v2_10.py compare suspect.txt baseline1.txt baseline2.txt --lang sv
    python ai_style_triage_v2_10.py sonify text.txt output.wav --lang sv
    python ai_style_triage_v2_10.py full text.txt --lang sv --json report.json --csv features.csv --wav text.wav
    python ai_style_triage_v2_10.py soundbank soundbank_dir
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import statistics
import wave
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, Sequence, Optional

try:
    import numpy as np
except ImportError:
    np = None


# ---------------------------------------------------------------------------
# SPRÅKREGLER
# ---------------------------------------------------------------------------

WORD_RE = re.compile(
    r"[A-Za-zÅÄÖåäöÉéÜüÕõÆæØø]+(?:[-'][A-Za-zÅÄÖåäöÉéÜüÕõÆæØø]+)?|\d+(?:[.,]\d+)?"
)
SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")

LANG = {
    "sv": {
        "conj": {"och", "eller"},
        "discourse": {
            "samtidigt", "därmed", "vidare", "däremot", "slutligen",
            "sammantaget", "dessutom", "således", "därför", "dock",
            "emellertid", "särskilt", "följaktligen", "samt",
        },
        "contrast": [
            ("inte", "utan"),
            ("inte", "enbart"),
            ("snarare", None),
        ],
        # ord som ofta signalerar satsgräns eller ny grammatisk struktur
        "hard_boundaries": {
            "att", "som", "när", "där", "eftersom", "medan", "om",
            "men", "dock", "vilket", "vilka", "vars", "då",
        },
        # vanliga bestämningar som gärna får följa med in i en nominalfras
        "phrase_helpers": {
            "en", "ett", "den", "det", "de", "sin", "sitt", "sina",
            "denna", "detta", "dessa", "deras", "barns", "olika",
            "flera", "många", "andra", "samma", "egna", "sociala",
        },
    },
    "en": {
        "conj": {"and", "or"},
        "discourse": {
            "however", "therefore", "thus", "moreover", "furthermore",
            "meanwhile", "overall", "particularly", "notably",
            "consequently", "additionally",
        },
        "contrast": [
            ("not", "but"),
            ("not", "only"),
            ("rather", None),
        ],
        "hard_boundaries": {
            "that", "which", "when", "where", "because", "while",
            "if", "but", "however", "whose",
        },
        "phrase_helpers": {
            "a", "an", "the", "this", "that", "these", "those",
            "their", "his", "her", "its", "some", "many", "several",
            "other", "same", "own", "social",
        },
    },
}


# Högprecisionsledtrådar för att skilja nominala fraspar från sats- och
# verbfras-kopplingar. Listorna är medvetet konservativa: om programmet är
# osäkert behandlas samordningen som satslik i stället för som en listsignal.
CLAUSE_CUES = {
    "sv": {
        "subjects": {
            "jag", "du", "han", "hon", "hen", "vi", "ni", "de", "dom",
            "man", "den", "det", "denna", "detta", "dessa", "någon",
            "något", "några", "alla", "barnet", "barnen", "pedagogen",
            "pedagogerna", "förskolläraren", "förskollärarna",
        },
        "finite_verbs": {
            "är", "var", "vore", "blir", "blev", "har", "hade", "ska",
            "skulle", "kan", "kunde", "kommer", "kom", "vill", "ville",
            "måste", "får", "fick", "bör", "borde", "gör", "gjorde",
            "finns", "fanns", "sker", "skedde", "visar", "visade",
            "beskriver", "beskrev", "menar", "menade", "säger", "sade",
            "ser", "såg", "anser", "ansåg", "upplever", "upplevde",
            "tycker", "tyckte", "tänker", "tänkte", "arbetar", "arbetade",
            "påverkar", "påverkade", "skapar", "skapade", "formar",
            "formade", "bidrar", "bidrog", "innebär", "innebar",
            "möjliggör", "möjliggjorde", "begränsar", "begränsade",
            "kräver", "krävde", "behöver", "behövde", "använder",
            "använde", "fungerar", "fungerade", "handlar", "handlade",
            "utgår", "utgick", "syftar", "syftade", "framträder",
            "framträdde", "betonar", "betonade", "lyfter", "lyfte",
            "etablerar", "etablerade", "agerar", "agerade", "samspelar",
            "samspelade", "organiserar", "organiserade", "öppnar", "öppnade",
            "minskar", "minskade", "ökar", "ökade", "uppstår", "uppstod",
            "reglerar", "reglerade", "reproducerar", "reproducerade",
            "bekräftar", "bekräftade", "presenterar", "presenterade",
            "resonerar", "resonerade", "förklarar", "förklarade",
            "diskuterar", "diskuterade", "tolkar", "tolkade", "kopplar",
            "kopplade", "stödjer", "stödde", "stöttar", "stöttade",
            "utvecklar", "utvecklade", "förändrar", "förändrade",
            "upprätthåller", "upprätthöll", "synliggör", "synliggjorde",
            "analyseras", "förstås", "formas", "används", "beskrivs",
            "regleras", "organiseras", "begränsas", "påverkas", "skapas",
            "tar", "tog", "ger", "gav", "går", "gick", "sätter", "satte",
            "hittar", "hittade", "deltar", "deltog", "delar", "delade",
            "bestämmer", "bestämde", "börjar", "började", "slutar",
            "slutade", "saknar", "saknade", "känner", "kände", "blivit",
        },
        "adverbial": {
            "inte", "också", "även", "sedan", "därefter", "därmed",
            "så", "ju", "bara", "ofta", "alltid", "aldrig", "fortfarande",
        },
    },
    "en": {
        "subjects": {
            "i", "you", "he", "she", "it", "we", "they", "one",
            "this", "that", "these", "those", "someone", "everyone",
            "the child", "children", "teachers",
        },
        "finite_verbs": {
            "is", "are", "was", "were", "be", "becomes", "became", "has",
            "have", "had", "does", "did", "can", "could", "will", "would",
            "shall", "should", "must", "may", "might", "shows", "showed",
            "describes", "described", "means", "meant", "says", "said",
            "sees", "saw", "thinks", "thought", "works", "worked",
            "affects", "affected", "creates", "created", "requires",
            "required", "uses", "used", "supports", "supported",
        },
        "adverbial": {
            "not", "also", "then", "therefore", "just", "often", "always",
            "never", "still",
        },
    },
}


# ---------------------------------------------------------------------------
# BASFUNKTIONER
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in SENT_RE.split(text) if s.strip()]


def mean(xs: Sequence[float]) -> float:
    return statistics.fmean(xs) if xs else 0.0


def stdev(xs: Sequence[float]) -> float:
    return statistics.pstdev(xs) if len(xs) > 1 else 0.0


def coef_var(xs: Sequence[float]) -> float:
    m = mean(xs)
    return (stdev(xs) / m) if m else 0.0


def safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def zscore(value: float, mu: float, sigma: float) -> float:
    if sigma <= 1e-9:
        return 0.0
    return (value - mu) / sigma


def normalized_entropy(xs: Sequence[int]) -> float:
    if len(xs) <= 1:
        return 0.0
    c = Counter(xs)
    n = sum(c.values())
    probs = [v / n for v in c.values()]
    H = -sum(p * math.log2(p) for p in probs if p > 0)
    Hmax = math.log2(len(c)) if len(c) > 1 else 1.0
    return safe_div(H, Hmax)


def ngrams(tokens: Sequence[str], n: int) -> Iterable[tuple[str, ...]]:
    for i in range(len(tokens) - n + 1):
        yield tuple(tokens[i:i+n])


# ---------------------------------------------------------------------------
# FÖRBÄTTRAD FRASEXTRAKTION FÖR OCH/ELLER
# ---------------------------------------------------------------------------

PUNCT_TOK_RE = re.compile(
    r"[A-Za-zÅÄÖåäöÉéÜüÕõÆæØø]+(?:[-'][A-Za-zÅÄÖåäöÉéÜüÕõÆæØø]+)?|\d+(?:[.,]\d+)?|[,.!?;:()]"
)


def tokenize_with_punct(text: str) -> list[str]:
    return [m.group(0) for m in PUNCT_TOK_RE.finditer(text)]


def is_word_token(tok: str) -> bool:
    return bool(WORD_RE.fullmatch(tok))


def phrase_boundary(tok: str, lang: str) -> bool:
    low = tok.lower()
    if tok in {".", "!", "?", ";", ":"}:
        return True
    if low in LANG[lang]["hard_boundaries"]:
        return True
    return False


def clean_phrase(tokens: list[str]) -> str:
    if not tokens:
        return ""
    s = " ".join(tokens)
    s = re.sub(r"\s+([,.;:!?])", r"\1", s)
    s = re.sub(r"\(\s+", "(", s)
    s = re.sub(r"\s+\)", ")", s)
    return s.strip(" ,;:")


def trim_phrase(tokens: list[str], max_words: int = 6) -> list[str]:
    """
    Begränsar frasen så att vi hellre får ett begripligt koordinationsled
    än en hel halv mening. Behåller högst max_words ord.
    """
    if not tokens:
        return []

    # Ta bort yttre skiljetecken.
    while tokens and tokens[0] in {",", "(", ")"}:
        tokens = tokens[1:]
    while tokens and tokens[-1] in {",", "(", ")"}:
        tokens = tokens[:-1]

    # Begränsa antal ord men behåll närmast konjunktionen.
    word_positions = [i for i, t in enumerate(tokens) if is_word_token(t)]
    if len(word_positions) <= max_words:
        return tokens

    # Standard för vänster/höger hanteras före anrop; här tar vi sista max_words.
    start = word_positions[-max_words]
    return tokens[start:]


def _take_last_words(tokens: list[str], n_words: int) -> list[str]:
    if n_words <= 0:
        return []
    positions = [i for i, t in enumerate(tokens) if is_word_token(t)]
    if len(positions) <= n_words:
        return tokens[:]
    return tokens[positions[-n_words]:]


def _take_first_words(tokens: list[str], n_words: int) -> list[str]:
    if n_words <= 0:
        return []
    positions = [i for i, t in enumerate(tokens) if is_word_token(t)]
    if len(positions) <= n_words:
        return tokens[:]
    return tokens[:positions[n_words - 1] + 1]


def extract_left_phrase(tokens: list[str], conj_i: int, lang: str, max_words: int = 6) -> list[str]:
    """
    Samla ett kandidatled till vänster. Den slutliga trimningen görs
    symmetriskt mot högerledet i coordination_records().
    """
    collected: list[str] = []
    word_count = 0
    i = conj_i - 1

    while i >= 0 and word_count < max_words:
        tok = tokens[i]

        if phrase_boundary(tok, lang):
            break
        if tok == ",":
            break
        if tok in {"(", ")"}:
            break

        collected.append(tok)
        if is_word_token(tok):
            word_count += 1
        i -= 1

    collected.reverse()
    return collected


def extract_right_phrase(tokens: list[str], conj_i: int, lang: str, max_words: int = 6) -> list[str]:
    """
    Samla kandidatled till höger. Stannar vid satsgräns, komma eller ny
    konjunktion. Första ledet efter konjunktionen prioriteras.
    """
    collected: list[str] = []
    word_count = 0
    i = conj_i + 1

    while i < len(tokens) and word_count < max_words:
        tok = tokens[i]

        if phrase_boundary(tok, lang):
            break
        if tok == ",":
            break
        if tok in {"(", ")"}:
            break
        if tok.lower() in LANG[lang]["conj"] and word_count > 0:
            break

        collected.append(tok)
        if is_word_token(tok):
            word_count += 1
        i += 1

    return collected


def extract_preceding_list_item(
    tokens: list[str],
    comma_i: int,
    lang: str,
    target_words: int,
    max_words: int = 6,
) -> list[str]:
    """
    Hitta A i A, B och C.

    För att undvika att få med inledande satsdelar använder vi längden på B
    som riktmärke. Om B är ett ord söker vi i första hand ett ord före kommat;
    om B är två ord söker vi två osv.
    """
    if comma_i < 0 or tokens[comma_i] != ",":
        return []

    collected: list[str] = []
    word_count = 0
    i = comma_i - 1

    while i >= 0 and word_count < max_words:
        tok = tokens[i]
        if phrase_boundary(tok, lang) or tok == "," or tok in {"(", ")"}:
            break
        collected.append(tok)
        if is_word_token(tok):
            word_count += 1
        i -= 1

    collected.reverse()

    # Matcha ungefär B:s storlek för att skära bort "Pedagogerna nämner ..."
    target = max(1, min(max_words, target_words))
    return _take_last_words(collected, target)


def _word_tokens(tokens: Sequence[str]) -> list[str]:
    return [t.lower() for t in tokens if is_word_token(t)]


def _high_confidence_verb(word: str, lang: str) -> bool:
    low = word.lower()
    cues = CLAUSE_CUES[lang]
    if low in cues["finite_verbs"]:
        return True

    if lang == "sv":
        # Passiva/perfektiva verbformer som är relativt säkra utan full
        # morfologisk analys. Några vanliga substantiv undantas uttryckligen.
        if low in {"insats", "plats", "sats", "ansats"}:
            return False
        return len(low) >= 7 and low.endswith(
            ("erats", "iserats", "ades", "erades", "ats", "its", "tts")
        )

    return len(low) >= 6 and low.endswith(("ated", "ized", "ised"))


def clause_likelihood(tokens: Sequence[str], lang: str) -> float:
    """
    Konservativ sannolikhet för att ett led innehåller en sats/verbfras.

    Detta är inte en grammatisk parser. Syftet är att undvika det tidigare
    felet där nästan varje kort utdrag automatiskt blev ett fraspar.
    """
    words = _word_tokens(tokens)
    if not words:
        return 1.0

    cues = CLAUSE_CUES[lang]
    strong_subjects = (
        {"jag", "du", "han", "hon", "hen", "vi", "ni", "de", "dom", "man"}
        if lang == "sv"
        else {"i", "you", "he", "she", "it", "we", "they", "one"}
    )
    subject_hit = any(w in cues["subjects"] for w in words)
    verb_hit = any(_high_confidence_verb(w, lang) for w in words)
    adverb_hit = any(w in cues["adverbial"] for w in words)

    score = 0.0
    if verb_hit:
        score += 0.58
    if words[0] in strong_subjects:
        score += 0.60
    elif words[0] in cues["subjects"]:
        score += 0.24
    elif subject_hit:
        score += 0.14
    if subject_hit and verb_hit:
        score += 0.20
    if adverb_hit and verb_hit:
        score += 0.08
    if len(words) >= 5:
        score += 0.12

    return clamp(score)


def _context_words(
    tokens: Sequence[str], conj_i: int, direction: int, max_words: int = 8
) -> list[str]:
    """Hämta närliggande ord utan att passera en tydlig meningsgräns."""
    out: list[str] = []
    i = conj_i + direction
    while 0 <= i < len(tokens) and len(out) < max_words:
        tok = tokens[i]
        if tok in {".", "!", "?", ";", ":"}:
            break
        if is_word_token(tok):
            if direction < 0:
                out.insert(0, tok.lower())
            else:
                out.append(tok.lower())
        i += direction
    return out


def coordination_audio_class(
    tokens: Sequence[str],
    conj_i: int,
    kind: str,
    left_tokens: Sequence[str],
    right_tokens: Sequence[str],
    first_tokens: Sequence[str],
    clause_score: float,
    structure_confidence: float,
    lang: str,
) -> tuple[str, str]:
    """Högprecisionsfilter för vilka samordningar som får höras.

    Analysindexet behåller den tidigare klassningen. Ljudlagret använder en
    striktare trevägsprincip: tydlig signal, tydlig sats/verbfras eller osäkert
    fall. Endast tydliga signaler får ljud.
    """
    if kind == "CLAUSE_OR_LONG":
        return "CLAUSE_SILENT", "grundklassningen är satslik eller för lång"

    left_context = _context_words(tokens, conj_i, -1)
    right_context = _context_words(tokens, conj_i, 1)
    left_words = _word_tokens(left_tokens)
    right_words = _word_tokens(right_tokens)
    first_words = _word_tokens(first_tokens)
    cues = CLAUSE_CUES[lang]

    left_verbs = [w for w in left_context if _high_confidence_verb(w, lang)]
    right_verbs = [w for w in right_context if _high_confidence_verb(w, lang)]
    subject_words = cues["subjects"]

    # Två verbdomäner kring konjunktionen är den starkaste satsindikatorn.
    if left_verbs and right_verbs:
        return "CLAUSE_SILENT", "verb finns på båda sidor om konjunktionen"

    # Ett nytt subjekt efter och/eller markerar normalt en ny sats. Även utan
    # säkert verb hålls fallet tyst enligt precision-först-principen.
    if right_context and right_context[0] in subject_words:
        return "CLAUSE_SILENT", "högerledet inleds med ett möjligt subjekt"

    # Verb precis intill konjunktionen fångar delade subjekt: sjunger och dansar.
    if (
        left_context and _high_confidence_verb(left_context[-1], lang)
    ) or (
        right_context and _high_confidence_verb(right_context[0], lang)
    ):
        return "CLAUSE_SILENT", "ett verb står intill konjunktionen"

    phrase_words = first_words + left_words + right_words
    if any(w in subject_words for w in phrase_words):
        return "UNCERTAIN_SILENT", "ett möjligt subjekt finns i frasleden"

    if any(w in cues["adverbial"] for w in phrase_words):
        return "UNCERTAIN_SILENT", "ett satsadverbial finns i frasleden"

    # v2.3 tillät värden strax under 0,58. Ljudlagret kräver nu helt låg
    # satslikhet och en tydligare lokal struktur.
    if clause_score >= 0.24:
        return "UNCERTAIN_SILENT", "satslikheten är inte tillräckligt låg"
    if structure_confidence < 0.78:
        return "UNCERTAIN_SILENT", "strukturens säkerhet är under 0,78"

    if kind == "TRIAD":
        return "TRIAD_SIGNAL", "tydligt nominalt treled"
    return "PAIR_SIGNAL", "tydligt nominalt fraspar"


def nominal_core_on_right(tokens: list[str], lang: str) -> list[str]:
    """Skär bort en efterföljande sats efter minst ett nominalt kärnord."""
    out: list[str] = []
    word_count = 0
    for tok in tokens:
        if is_word_token(tok):
            if word_count >= 1 and _high_confidence_verb(tok, lang):
                break
            word_count += 1
        out.append(tok)
    return out


def coordination_signature(record: dict) -> str:
    """Normaliserad signatur för repetitionsdämpning och diversitetsmått."""
    parts = [
        " ".join(tokenize(record.get("first_phrase_if_triad", ""))),
        " ".join(tokenize(record.get("left_phrase", ""))),
        record.get("conjunction", ""),
        " ".join(tokenize(record.get("right_phrase", ""))),
    ]
    return "|".join(parts)


def coordination_records(text: str, lang: str) -> list[dict]:
    """
    Returnerar alla och/eller-samordningar med frasutdrag.

    Princip:
    - högerledet fungerar som ankare,
    - vänsterledet trimmas till ungefär samma storlek,
    - vid A, B och C används B:s storlek för att hitta A.

    Detta är fortfarande en transparent heuristik, inte full syntaktisk parsning.
    """
    raw = tokenize_with_punct(text)
    out: list[dict] = []

    word_index = 0

    for i, tok in enumerate(raw):
        current_word_index = word_index
        if is_word_token(tok):
            word_index += 1

        if tok.lower() not in LANG[lang]["conj"]:
            continue

        left_candidate = extract_left_phrase(raw, i, lang)
        right_candidate = nominal_core_on_right(
            extract_right_phrase(raw, i, lang), lang
        )

        rw = len([t for t in right_candidate if is_word_token(t)])
        lw_raw = len([t for t in left_candidate if is_word_token(t)])

        # Om högerledet är kort, trimma vänsterledet till ungefär samma längd.
        # Tillåt ett extra ord på vänster sida när högerledet är mycket kort.
        if rw > 0:
            left_target = rw if rw >= 2 else min(2, max(1, lw_raw))
            left_tokens = _take_last_words(left_candidate, left_target)
        else:
            left_tokens = _take_last_words(left_candidate, min(3, lw_raw))

        right_tokens = _take_first_words(right_candidate, min(6, max(1, rw)))

        # Finns komma omedelbart före det extraherade vänsterledet?
        # Leta utifrån originalpositionen: gå bakåt över vänsterledets ord.
        j = i - 1
        words_to_skip = len([t for t in left_tokens if is_word_token(t)])
        seen = 0
        while j >= 0 and seen < words_to_skip:
            if is_word_token(raw[j]):
                seen += 1
            j -= 1

        # hoppa över eventuella mellanslag finns ej i tokenlistan; j pekar nu
        # på token före vänsterledet.
        comma_i = j if j >= 0 and raw[j] == "," else -1

        middle_words = len([t for t in left_tokens if is_word_token(t)])
        first_tokens = extract_preceding_list_item(
            raw, comma_i, lang, target_words=max(1, middle_words)
        ) if comma_i >= 0 else []

        left = clean_phrase(left_tokens)
        right = clean_phrase(right_tokens)
        first = clean_phrase(first_tokens)

        lw = len(tokenize(left))
        rw2 = len(tokenize(right))

        parallel = 0.0
        if lw and rw2:
            length_similarity = 1.0 - (abs(lw - rw2) / max(lw, rw2))
            shortness = 1.0 if max(lw, rw2) <= 5 else 0.5
            parallel = clamp(0.7 * length_similarity + 0.3 * shortness)

        left_clause = clause_likelihood(left_tokens, lang)
        right_clause = clause_likelihood(right_tokens, lang)
        first_clause = clause_likelihood(first_tokens, lang) if first_tokens else 0.0
        clause_score = max(left_clause, right_clause, first_clause)

        lengths = [n for n in (len(tokenize(first)), lw, rw2) if n > 0]
        balance = safe_div(min(lengths), max(lengths)) if lengths else 0.0

        if (
            first and left and right
            and max(lengths, default=99) <= 5
            and balance >= 0.34
            and clause_score < 0.58
        ):
            kind = "TRIAD"
        elif (
            left and right
            and max(lw, rw2) <= 5
            and safe_div(min(lw, rw2), max(lw, rw2)) >= 0.40
            and clause_score < 0.58
        ):
            kind = "PHRASE_PAIR"
        else:
            kind = "CLAUSE_OR_LONG"

        structure_confidence = 0.0
        if kind != "CLAUSE_OR_LONG":
            structure_confidence = clamp(
                0.52 * parallel
                + 0.28 * balance
                + 0.20 * (1.0 - clause_score)
            )

        audio_class, audio_filter_reason = coordination_audio_class(
            raw,
            i,
            kind,
            left_tokens,
            right_tokens,
            first_tokens,
            clause_score,
            structure_confidence,
            lang,
        )

        out.append({
            "word_index": current_word_index,
            "conjunction": tok.lower(),
            "left_phrase": left,
            "right_phrase": right,
            "first_phrase_if_triad": first,
            "kind": kind,
            "parallelism": parallel,
            "clause_likelihood": clause_score,
            "structure_confidence": structure_confidence,
            "audio_class": audio_class,
            "audio_filter_reason": audio_filter_reason,
        })

    return out


def add_sentence_context(text: str, records: list[dict], lang: str) -> list[dict]:
    """Lägg transparent meningskontext på varje samordning och ljudfiltrera.

    Kontextreglerna är avsedda att skilja korta strukturerade samordningar
    från B-liknande satskedjor. De ändrar inte grundklassning eller index.
    """
    and_word = "och" if lang == "sv" else "and"
    contexts: list[dict] = []
    start = 0

    for sentence_index, sentence in enumerate(split_sentences(text)):
        stoks = tokenize(sentence)
        end = start + len(stoks)
        contexts.append({
            "sentence_index": sentence_index,
            "start": start,
            "end": end,
            "word_count": len(stoks),
            "and_count": stoks.count(and_word),
        })
        start = end

    context_i = 0
    for record in records:
        widx = int(record.get("word_index", 0))
        while (
            context_i + 1 < len(contexts)
            and widx >= contexts[context_i]["end"]
        ):
            context_i += 1

        ctx = contexts[context_i] if contexts else {
            "sentence_index": 0,
            "start": 0,
            "end": max(1, start),
            "word_count": max(1, start),
            "and_count": 0,
        }
        position = max(0, widx - int(ctx["start"]))
        is_primary_and = record.get("conjunction") == and_word
        initial_and = is_primary_and and position == 0
        five_plus_and = is_primary_and and int(ctx["and_count"]) >= 5
        long_multi_and = (
            is_primary_and
            and int(ctx["word_count"]) > 20
            and int(ctx["and_count"]) >= 3
        )

        record.update({
            "sentence_index": int(ctx["sentence_index"]),
            "sentence_word_count": int(ctx["word_count"]),
            "and_count_in_sentence": int(ctx["and_count"]),
            "conjunction_position_in_sentence": position,
            "sentence_initial_and": initial_and,
            "five_plus_and_sentence": five_plus_and,
            "long_multi_and_sentence": long_multi_and,
        })

        if initial_and:
            record["audio_class"] = "CONTEXT_SILENT"
            record["audio_filter_reason"] = "meningsinledande och är en diskurskoppling"
            record["density_context_penalty"] = 0.0
        elif five_plus_and:
            record["audio_class"] = "CONTEXT_SILENT"
            record["audio_filter_reason"] = "meningen innehåller minst fem och och behandlas som satskedja"
            record["density_context_penalty"] = 0.12
        elif long_multi_and and record.get("audio_class") == "PAIR_SIGNAL":
            record["audio_class"] = "CONTEXT_SILENT"
            record["audio_filter_reason"] = "fraspar i lång mening med minst tre och behandlas som satskedja"
            record["density_context_penalty"] = 0.12
        else:
            record["density_context_penalty"] = 0.0

    return records


# ---------------------------------------------------------------------------
# KONTRAST, N-GRAMS OCH LOKALA KLUSTER
# ---------------------------------------------------------------------------

def count_contrast_sentences(sentences: Sequence[str], lang: str) -> int:
    total = 0
    for s in sentences:
        toks = tokenize(s)
        tokset = set(toks)
        for a, b in LANG[lang]["contrast"]:
            if b is None:
                if a in tokset:
                    total += 1
                    break
            else:
                if a in tokset and b in tokset and toks.index(a) < toks.index(b):
                    total += 1
                    break
    return total


def window_counts(indices: Sequence[int], window: int) -> list[int]:
    out = []
    j = 0
    for i in range(len(indices)):
        if j < i:
            j = i
        while j < len(indices) and indices[j] - indices[i] <= window:
            j += 1
        out.append(j - i)
    return out


# ---------------------------------------------------------------------------
# FEATURESET
# ---------------------------------------------------------------------------

@dataclass
class FeatureSet:
    language: str
    words: int
    sentences: int

    conjunction_count: int
    conjunction_rate: float
    and_count: int
    and_rate: float
    or_count: int
    or_rate: float
    conjunction_gap_mean: float
    conjunction_gap_cv: float
    conjunction_gap_entropy: float

    sentence_initial_and_count: int
    sentences_with_5plus_and: int
    and_in_5plus_and_sentences: int
    long_multi_and_sentence_count: int

    phrase_pair_count: int
    triad_count: int
    clause_or_long_count: int
    phrase_pair_ratio: float
    clause_like_conj_ratio: float
    mean_coordination_parallelism: float
    weighted_structured_coordination: float
    structured_coordination_rate: float
    weighted_triad_rate: float
    coordination_signature_diversity: float
    coordination_repeat_share: float

    contrast_sentence_count: int
    contrast_sentence_rate: float

    sentence_len_mean: float
    sentence_len_cv: float

    discourse_marker_rate: float

    repeated_4gram_rate: float
    top_4gram_share: float
    distributed_4gram_repetition: float

    type_token_ratio: float
    long_word_rate: float

    local_conj_peak_120: int
    local_conj_peak_180: int

    template_score: float
    variability_score: float
    anomaly_index: float


def extract_features(text: str, lang: str) -> tuple[FeatureSet, list[dict]]:
    if lang not in LANG:
        raise ValueError("lang must be 'sv' or 'en'")

    toks = tokenize(text)
    sents = split_sentences(text)
    sent_tokens = [tokenize(s) for s in sents]
    sent_lens = [len(x) for x in sent_tokens if x]

    conj_set = LANG[lang]["conj"]
    conj_idx = [i for i, tok in enumerate(toks) if tok in conj_set]
    conj_gaps = [conj_idx[i] - conj_idx[i - 1] for i in range(1, len(conj_idx))]

    coords = add_sentence_context(text, coordination_records(text, lang), lang)
    phrase_pairs = [x for x in coords if x["kind"] == "PHRASE_PAIR"]
    triads = [x for x in coords if x["kind"] == "TRIAD"]
    clauses = [x for x in coords if x["kind"] == "CLAUSE_OR_LONG"]
    structured = phrase_pairs + triads

    weighted_structured = sum(x["structure_confidence"] for x in structured)
    weighted_triads = sum(x["structure_confidence"] for x in triads)
    signatures = [coordination_signature(x) for x in structured]
    signature_counts = Counter(signatures)

    contrast_count = count_contrast_sentences(sents, lang)
    discourse_hits = sum(1 for tok in toks if tok in LANG[lang]["discourse"])

    ng = list(ngrams(toks, 4))
    ng_counter = Counter(ng)
    repeated_ngrams = sum(c for c in ng_counter.values() if c > 1)
    top_4gram = ng_counter.most_common(1)[0][1] if ng_counter else 0

    w120 = window_counts(conj_idx, 120) if conj_idx else []
    w180 = window_counts(conj_idx, 180) if conj_idx else []

    and_word = "och" if lang == "sv" else "and"
    or_word = "eller" if lang == "sv" else "or"
    and_count = toks.count(and_word)
    or_count = toks.count(or_word)
    and_rate = safe_div(and_count, len(toks))
    or_rate = safe_div(or_count, len(toks))
    sentence_initial_and_count = sum(
        1 for stoks in sent_tokens if stoks and stoks[0] == and_word
    )
    sentences_with_5plus_and = sum(
        1 for stoks in sent_tokens if stoks.count(and_word) >= 5
    )
    and_in_5plus_and_sentences = sum(
        stoks.count(and_word)
        for stoks in sent_tokens
        if stoks.count(and_word) >= 5
    )
    long_multi_and_sentence_count = sum(
        1
        for stoks in sent_tokens
        if len(stoks) > 20 and stoks.count(and_word) >= 3
    )

    conjunction_rate = safe_div(len(conj_idx), len(toks))
    phrase_pair_ratio = safe_div(len(phrase_pairs) + len(triads), max(1, len(coords)))
    clause_ratio = safe_div(len(clauses), max(1, len(coords)))
    parallelism = mean([x["parallelism"] for x in coords])
    gap_cv = coef_var(conj_gaps)
    gap_ent = normalized_entropy(conj_gaps)
    sent_cv = coef_var(sent_lens)
    repeated_4gram_rate = safe_div(repeated_ngrams, max(1, len(ng)))
    top_4gram_share = safe_div(top_4gram, max(1, len(ng)))

    # Upprepning är mer intressant när den är spridd över flera mallar. Om en
    # enda fras står för en stor del (t.ex. samma ämnesterm om och om igen)
    # dämpas signalen, eftersom det ofta är ämnesbunden repetition.
    repetition_spread = 1.0 - clamp((top_4gram_share - 0.001) / 0.010)
    distributed_repetition = repeated_4gram_rate * repetition_spread

    structured_rate = safe_div(weighted_structured, len(toks))
    triad_rate = safe_div(weighted_triads, len(toks))
    signature_diversity = safe_div(len(signature_counts), len(signatures))
    repeat_share = safe_div(
        max(signature_counts.values(), default=0), len(signatures)
    )

    # v2.1: rå mängd "och" är inte längre huvudsignal. I stället vägs
    # strukturerade och varierade fraspar/treled, kontrastmallar och spridd
    # frasrepetition samman. Detta gör satsbindande "och" till en motvikt.
    template_score = (
        0.25 * clamp(((structured_rate * 1000) - 18.0) / 12.0) +
        0.22 * clamp(((triad_rate * 1000) - 1.0) / 5.0) +
        0.18 * clamp((safe_div(contrast_count, len(sents)) - 0.010) / 0.070) +
        0.08 * clamp((safe_div(discourse_hits, len(toks)) - 0.006) / 0.008) +
        0.17 * clamp((distributed_repetition - 0.025) / 0.075) +
        0.10 * clamp((safe_div(sum(1 for t in toks if len(t) >= 9), len(toks)) - 0.14) / 0.10)
    )

    # Satslik samordning, en enda dominerande fras och stor meningsvariation
    # fungerar som motvikter. Repeat-komponenten börjar först över 2 procent.
    variability_score = (
        0.55 * clamp(clause_ratio / 0.60) +
        0.30 * clamp((repeat_share - 0.02) / 0.12) +
        0.15 * clamp(sent_cv / 1.0)
    )

    anomaly_index = clamp(
        0.82 * template_score
        - 0.20 * variability_score
        + 0.12
    )

    fs = FeatureSet(
        language=lang,
        words=len(toks),
        sentences=len(sents),

        conjunction_count=len(conj_idx),
        conjunction_rate=conjunction_rate,
        and_count=and_count,
        and_rate=and_rate,
        or_count=or_count,
        or_rate=or_rate,
        conjunction_gap_mean=mean(conj_gaps),
        conjunction_gap_cv=gap_cv,
        conjunction_gap_entropy=gap_ent,

        sentence_initial_and_count=sentence_initial_and_count,
        sentences_with_5plus_and=sentences_with_5plus_and,
        and_in_5plus_and_sentences=and_in_5plus_and_sentences,
        long_multi_and_sentence_count=long_multi_and_sentence_count,

        phrase_pair_count=len(phrase_pairs),
        triad_count=len(triads),
        clause_or_long_count=len(clauses),
        phrase_pair_ratio=phrase_pair_ratio,
        clause_like_conj_ratio=clause_ratio,
        mean_coordination_parallelism=parallelism,
        weighted_structured_coordination=weighted_structured,
        structured_coordination_rate=structured_rate,
        weighted_triad_rate=triad_rate,
        coordination_signature_diversity=signature_diversity,
        coordination_repeat_share=repeat_share,

        contrast_sentence_count=contrast_count,
        contrast_sentence_rate=safe_div(contrast_count, len(sents)),

        sentence_len_mean=mean(sent_lens),
        sentence_len_cv=sent_cv,

        discourse_marker_rate=safe_div(discourse_hits, len(toks)),

        repeated_4gram_rate=repeated_4gram_rate,
        top_4gram_share=top_4gram_share,
        distributed_4gram_repetition=distributed_repetition,

        type_token_ratio=safe_div(len(set(toks)), len(toks)),
        long_word_rate=safe_div(sum(1 for t in toks if len(t) >= 9), len(toks)),

        local_conj_peak_120=max(w120) if w120 else 0,
        local_conj_peak_180=max(w180) if w180 else 0,

        template_score=template_score,
        variability_score=variability_score,
        anomaly_index=anomaly_index,
    )

    return fs, coords


# ---------------------------------------------------------------------------
# TOLKNING
# ---------------------------------------------------------------------------

def band(index: float) -> str:
    if index < 0.33:
        return "Låg stilistisk avvikelse"
    if index < 0.66:
        return "Måttlig stilistisk avvikelse"
    return "Hög stilistisk avvikelse"


def explain(fs: FeatureSet) -> list[str]:
    reasons = []

    if fs.structured_coordination_rate > 0.026:
        reasons.append("Hög frekvens av tydligt strukturerade fraspar och treled")

    if fs.weighted_triad_rate > 0.004:
        reasons.append("Många balanserade treled per tusen ord")

    if fs.contrast_sentence_rate > 0.05:
        reasons.append("Kontrastkonstruktioner återkommer systematiskt")

    if fs.distributed_4gram_repetition > 0.08:
        reasons.append("Återkommande frasmönster är spridda över flera formuleringar")

    if fs.coordination_signature_diversity > 0.90:
        reasons.append("De strukturerade samordningarna är lexikalt varierade")

    if fs.clause_like_conj_ratio > 0.38:
        reasons.append("Många och/eller binder satser eller verbfraser; detta dämpar signalen")

    if fs.sentences_with_5plus_and > 0 or fs.long_multi_and_sentence_count >= 3:
        reasons.append("Flera och ligger i långa satskedjor; dessa filtreras bort ur ljudsignalen")

    if fs.coordination_repeat_share > 0.08:
        reasons.append("En liten mängd ämnesfraser upprepas ofta; dessa dämpas i ljudet")

    if fs.sentence_len_cv > 0.65:
        reasons.append("Meningslängden varierar tydligt")

    if not reasons:
        reasons.append("Inga starka enskilda avvikelsesignaler")

    return reasons


# ---------------------------------------------------------------------------
# BASELINE-JÄMFÖRELSE
# ---------------------------------------------------------------------------

def compare_against_baseline(suspect: FeatureSet, baselines: list[FeatureSet]) -> dict:
    numeric_fields = [
        "conjunction_rate",
        "and_rate",
        "or_rate",
        "conjunction_gap_mean",
        "conjunction_gap_cv",
        "conjunction_gap_entropy",
        "phrase_pair_ratio",
        "clause_like_conj_ratio",
        "mean_coordination_parallelism",
        "structured_coordination_rate",
        "weighted_triad_rate",
        "coordination_signature_diversity",
        "coordination_repeat_share",
        "contrast_sentence_rate",
        "sentence_len_mean",
        "sentence_len_cv",
        "discourse_marker_rate",
        "repeated_4gram_rate",
        "top_4gram_share",
        "distributed_4gram_repetition",
        "type_token_ratio",
        "long_word_rate",
        "local_conj_peak_120",
        "local_conj_peak_180",
        "template_score",
        "variability_score",
        "anomaly_index",
    ]

    rows = []
    total_abs_z = 0.0

    for field in numeric_fields:
        vals = [getattr(b, field) for b in baselines]
        mu = mean(vals)
        sigma = stdev(vals)
        val = getattr(suspect, field)
        z = zscore(val, mu, sigma)
        total_abs_z += abs(z)
        rows.append({
            "feature": field,
            "suspect": val,
            "baseline_mean": mu,
            "baseline_sd": sigma,
            "zscore": z,
        })

    rows.sort(key=lambda r: abs(r["zscore"]), reverse=True)

    return {
        "baseline_n": len(baselines),
        "mean_absolute_z": safe_div(total_abs_z, len(numeric_fields)),
        "largest_differences": rows[:8],
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# SONIFIERING
# ---------------------------------------------------------------------------

SR = 44100
TWOPI = 2 * math.pi
WORDS_PER_TICK = 30
WORDS_PER_SECOND = 200.0
TIME_MARKER_INTERVAL = WORDS_PER_TICK / WORDS_PER_SECOND
LEAD_IN_SECONDS = 0.45
TAIL_SECONDS = 0.85
PHRASE_PAIR_INTERVAL = 0.120
TIME_MARKER_GAIN = 0.26
DENSITY_LEVEL_1 = 4.0
DENSITY_LEVEL_2 = 5.0
DENSITY_LEVEL_3 = 6.0
WOW_DENSITY_THRESHOLD = 5.5
DENSITY_PAIR_WEIGHT = 0.50
DENSITY_TRIAD_WEIGHT = 2.00
DENSITY_CLAUSE_PENALTY = 0.12


def require_numpy():
    if np is None:
        raise RuntimeError(
            "Sonifiering kräver numpy. Installera med: pip install numpy"
        )


def peak_normalize(y, target=0.22):
    pk = float(np.max(np.abs(y))) if len(y) else 0.0
    if pk <= 1e-9:
        return y.astype(np.float32)
    return (y * (target / pk)).astype(np.float32)


def envelope(n: int, attack_s: float, decay_s: float):
    env = np.zeros(n, dtype=np.float32)
    a = min(n, max(1, int(attack_s * SR)))
    d = min(n - a, max(1, int(decay_s * SR)))
    env[:a] = np.linspace(0, 1, a, endpoint=False)
    if d > 0:
        env[a:a+d] = np.linspace(1, 0, d, endpoint=False)
    return env


def make_word_clock_tick():
    """Ett ensamt, lågt tick för ordklockans 30-ordsmarkeringar."""
    n = int(0.055 * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(3)
    noise = rng.standard_normal(n).astype(np.float32)
    kernel = np.ones(13, dtype=np.float32) / 13.0
    muted_noise = np.convolve(noise, kernel, mode="same").astype(np.float32)
    tone = (
        0.72 * np.sin(TWOPI * 690 * t)
        + 0.28 * np.sin(TWOPI * 1030 * t)
    ).astype(np.float32)
    decay = np.exp(-58.0 * t).astype(np.float32)
    y = (0.22 * muted_noise + 0.78 * tone) * decay
    y *= envelope(n, 0.0008, 0.052)
    return peak_normalize(y, target=0.085)


def mix_samples(events: Sequence[tuple[float, object]], tail_s: float = 0.10):
    """Mixa (starttid, sample)-par till en mono-array."""
    end = max((ts + len(sample) / SR for ts, sample in events), default=0.0)
    y = np.zeros(max(1, int((end + tail_s) * SR)), dtype=np.float32)
    for ts, sample in events:
        i = int(ts * SR)
        j = i + len(sample)
        if j > len(y):
            y = np.pad(y, (0, j - len(y)))
        y[i:j] += sample
    return y


def make_pinball_bell(freq: float = 880.0, duration_s: float = 0.23):
    """Ljus metallisk flipperklocka utan att efterlikna ett specifikt spel."""
    n = int(duration_s * SR)
    t = np.arange(n, dtype=np.float32) / SR
    phase = TWOPI * (freq * t + 0.55 * (1.0 - np.exp(-28.0 * t)))
    y = (
        np.sin(phase)
        + 0.46 * np.sin(2.013 * phase + 0.20)
        + 0.21 * np.sin(3.97 * phase + 0.55)
        + 0.09 * np.sin(6.11 * phase)
    ).astype(np.float32)
    metallic_decay = (1.0 - np.exp(-650.0 * t)) * np.exp(-13.5 * t)
    y *= metallic_decay.astype(np.float32)
    return peak_normalize(y, target=0.145)


def make_phrase_pair_figure():
    """Två korta flippertoner, låg–hög, för ett strukturerat fraspar."""
    low = make_pinball_bell(493.88, duration_s=0.17)
    high = make_pinball_bell(659.25, duration_s=0.17)
    y = mix_samples([
        (0.000, low * 0.82),
        (PHRASE_PAIR_INTERVAL, high * 0.76),
    ], tail_s=0.07)
    return peak_normalize(y, target=0.135)


def make_carnival_note(freq: float = 440.0, duration_s: float = 0.22):
    """Mjuk calliope-liknande tivoliton för kontrastfiguren."""
    n = int(duration_s * SR)
    t = np.arange(n, dtype=np.float32) / SR
    vibrato = 1.0 + 0.007 * np.sin(TWOPI * 5.4 * t)
    phase = np.cumsum((TWOPI * freq / SR) * vibrato).astype(np.float32)
    y = (
        np.sin(phase)
        + 0.30 * np.sin(3.0 * phase)
        + 0.12 * np.sin(5.0 * phase)
    ).astype(np.float32)
    y *= envelope(n, 0.006, max(0.001, duration_s - 0.006))
    return peak_normalize(y, target=0.115)


def make_mechanical_warning_pulse(duration_s: float = 0.34):
    """Lågt raspigt larmpulsljud utan flipperklockornas metalliska tonhöjd."""
    n = int(duration_s * SR)
    t = np.arange(n, dtype=np.float32) / SR
    inst_freq = 155.0 - 62.0 * (t / duration_s) + 9.0 * np.sin(TWOPI * 7.5 * t)
    phase = np.cumsum(TWOPI * inst_freq / SR).astype(np.float32)

    # En låg, ojämn maskin-/klaxonkropp. Udda övertoner och amplitudhack gör
    # den kategoriskt annorlunda än de rena stigande flipperfigurerna.
    buzz = (
        np.sin(phase)
        + 0.48 * np.sin(3.0 * phase + 0.25)
        + 0.24 * np.sin(5.0 * phase + 0.60)
    ).astype(np.float32)
    gate = (0.58 + 0.42 * (np.sin(TWOPI * 18.0 * t) > -0.15)).astype(np.float32)
    env = (1.0 - np.exp(-90.0 * t)) * np.exp(-5.2 * t)
    y = buzz * gate * env.astype(np.float32)
    return peak_normalize(y, target=0.13)


def make_density_alarm():
    """Två låga mekaniska larmpulser för lokal strukturtäthet."""
    pulse = make_mechanical_warning_pulse()
    y = mix_samples([
        (0.000, pulse),
        (0.255, pulse * 0.88),
    ], tail_s=0.10)
    return peak_normalize(y, target=0.155)


def make_extreme_wow_sweep(duration_s: float = 0.92):
    """Kontinuerligt formantsvep med brusfinal för programmets extremnivå."""
    n = int(duration_s * SR)
    t = np.arange(n, dtype=np.float32) / SR
    x = t / duration_s

    # En obruten upp–ned-rörelse ger ett hörbart "wow" snarare än ännu ett
    # klockarpeggio. Formantbanden gör ljudet mer röst-/sirénlikt.
    f0 = np.where(
        x < 0.58,
        175.0 + 355.0 * (x / 0.58) ** 1.25,
        530.0 - 250.0 * ((x - 0.58) / 0.42),
    ).astype(np.float32)
    phase = np.cumsum(TWOPI * f0 / SR).astype(np.float32)
    voice = (
        np.sin(phase)
        + 0.38 * np.sin(2.0 * phase + 0.35)
        + 0.22 * np.sin(3.0 * phase + 1.10)
    ).astype(np.float32)
    formant = (0.70 + 0.30 * np.sin(TWOPI * (720.0 + 260.0 * x) * t)).astype(np.float32)

    rng = np.random.default_rng(2808)
    noise = rng.normal(0.0, 1.0, n).astype(np.float32)
    kernel = np.ones(11, dtype=np.float32) / 11.0
    soft_noise = np.convolve(noise, kernel, mode="same").astype(np.float32)
    final_burst = np.clip((x - 0.70) / 0.30, 0.0, 1.0).astype(np.float32)

    env = np.sin(np.pi * np.clip(x, 0.0, 1.0)) ** 0.65
    y = (0.88 * voice * formant + 0.22 * soft_noise * final_burst) * env
    return peak_normalize(y.astype(np.float32), target=0.18)


def write_wav(path: Path, y):
    y = np.clip(y, -0.98, 0.98)
    pcm = (y * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def build_soundbank() -> dict[str, object]:
    """Bygg samtliga ljudfigurer som används i sonifieringen."""
    triad_bells = [make_pinball_bell(f) for f in (739.99, 932.33, 1174.66)]
    triad_demo = mix_samples([
        (0.000, triad_bells[0]),
        (0.115, triad_bells[1] * 0.90),
        (0.230, triad_bells[2] * 0.82),
    ], tail_s=0.10)

    contrast_notes = [
        make_carnival_note(392.00),
        make_carnival_note(523.25),
    ]
    contrast_demo = mix_samples([
        (0.000, contrast_notes[0]),
        (0.160, contrast_notes[1] * 0.92),
    ], tail_s=0.10)

    return {
        "00_ordklocka_tick_var_30e_ord.wav": make_word_clock_tick(),
        "01_fraspar_flipper_lag_hog.wav": make_phrase_pair_figure(),
        "02_treled_flipperklockor.wav": peak_normalize(triad_demo, target=0.18),
        "03_tathetsvarning_mekaniskt_dubbellarm.wav": make_density_alarm(),
        "04_kontrast_tivolisignal.wav": peak_normalize(contrast_demo, target=0.16),
        "05_extremkluster_wow_svep.wav": make_extreme_wow_sweep(),
    }


def export_soundbank(output_dir: Path) -> dict:
    require_numpy()
    output_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for filename, sample in build_soundbank().items():
        path = output_dir / filename
        write_wav(path, sample)
        written.append(str(path))
    return {
        "directory": str(output_dir),
        "files": written,
        "sample_rate": SR,
        "channels": 1,
        "bits_per_sample": 16,
        "word_clock_sound_included": True,
    }


def sonify(text: str, lang: str, output: Path) -> dict:
    """
    Sonifierar textens indikatorer.

    Ljudlogik i v2.10:
    - Ordklocka: ett lågt tick efter varje 30 ord.
    - Tydliga nominala fraspar A och B: två flipperljud, låg–hög.
    - Treled A, B och C: tre stigande flipperklockor.
    - Sats-, verbfras- och osäkra kopplingar: inget analysljud.
    - Meningsinledande och samt B-liknande satskedjor: inget analysljud.
    - Exakt upprepade samordningar tonas successivt ned.
    - Täta strukturella kluster: treled väger 2,0, par 0,5 och satslik
      samordning dämpar lokalt med 0,12; klustret ger mekaniskt dubbellarm.
    - Kontrastmeningar: kort tvåtonsfigur med tivolikaraktär.
    - Särskilt starka kluster från 5,5: långt wow-svep med brusfinal, högst
      en gång per 180 ord och bara vid globalt avvikelseindex minst 0,50.

    Tidsaxeln använder 200 ord per sekund. Ett 30-ordstick kommer därför var
    0,15 sekund, medan ljudfilens totala längd följer textens ordantal. Alla
    analysljud placeras med samma ordklocka. Slutnivån följer det
    evidensviktade indexet och normaliseras inte upp till samma toppnivå för
    varje text.
    """
    require_numpy()

    fs, coords = extract_features(text, lang)
    time_tick = make_word_clock_tick()
    phrase_pair = make_phrase_pair_figure()
    triad_bells = [make_pinball_bell(f) for f in (739.99, 932.33, 1174.66)]
    contrast_hits = [
        make_carnival_note(392.00),
        make_carnival_note(523.25),
    ]
    density_alarm = make_density_alarm()
    extreme_wow = make_extreme_wow_sweep()

    indicator_events = []
    time_marker_events = []
    total_words = max(1, fs.words)
    content_seconds = total_words / WORDS_PER_SECOND
    canvas_seconds = LEAD_IN_SECONDS + content_seconds + TAIL_SECONDS
    signature_seen: Counter[str] = Counter()
    density_recent: list[tuple[int, float]] = []
    last_density_word = -10_000
    last_jackpot_word = -10_000

    audible_coordination_count = 0
    suppressed_clause_count = 0
    suppressed_uncertain_count = 0
    suppressed_context_count = 0
    audible_pair_count = 0
    audible_triad_count = 0
    repeated_attenuated_count = 0
    density_alert_count = 0
    jackpot_count = 0

    for record in coords:
        widx = int(record.get("word_index", 0))
        tsec = LEAD_IN_SECONDS + (widx / WORDS_PER_SECOND)
        audio_class = record.get("audio_class", "UNCERTAIN_SILENT")

        density_recent = [
            (idx, weight)
            for idx, weight in density_recent
            if widx - idx <= 180
        ]
        density_weight = 0.0

        if audio_class == "CLAUSE_SILENT":
            suppressed_clause_count += 1
            density_weight = -DENSITY_CLAUSE_PENALTY
        elif audio_class == "UNCERTAIN_SILENT":
            suppressed_uncertain_count += 1
        elif audio_class == "CONTEXT_SILENT":
            suppressed_context_count += 1
            density_weight = -float(record.get("density_context_penalty", 0.0))
        else:
            signature = coordination_signature(record)
            occurrence = signature_seen[signature]
            signature_seen[signature] += 1
            novelty = 1.0 / math.sqrt(occurrence + 1.0)
            if occurrence:
                repeated_attenuated_count += 1

            confidence = float(record.get("structure_confidence", 0.0))
            gain = novelty * (0.45 + 0.55 * confidence)

            if audio_class == "TRIAD_SIGNAL":
                for j, (bell, step_gain) in enumerate(zip(
                    triad_bells, (1.00, 0.90, 0.82)
                )):
                    indicator_events.append((tsec + j * 0.115, bell * gain * step_gain))
                audible_triad_count += 1
                density_weight = DENSITY_TRIAD_WEIGHT * confidence * novelty
            else:
                indicator_events.append((tsec, phrase_pair * gain))
                audible_pair_count += 1
                density_weight = DENSITY_PAIR_WEIGHT * confidence * novelty

            audible_coordination_count += 1

        density_recent.append((widx, density_weight))
        local_density = max(0.0, sum(weight for _, weight in density_recent))

        level = 0
        if local_density >= DENSITY_LEVEL_3:
            level = 3
        elif local_density >= DENSITY_LEVEL_2:
            level = 2
        elif local_density >= DENSITY_LEVEL_1:
            level = 1

        if density_weight > 0 and level and (widx - last_density_word) >= 180:
            indicator_events.append((tsec + 0.18, density_alarm * (0.38 + 0.07 * level)))
            density_alert_count += 1
            last_density_word = widx

        # Wow har egen spärrtid och kan därför återkomma oberoende av när ett
        # svagare täthetslarm senast spelades.
        if (
            density_weight > 0
            and local_density >= WOW_DENSITY_THRESHOLD
            and fs.anomaly_index >= 0.50
            and (widx - last_jackpot_word) >= 180
        ):
            indicator_events.append((tsec + 0.26, extreme_wow * 0.32))
            jackpot_count += 1
            last_jackpot_word = widx

    # Kontrastmeningar placeras proportionellt i tidslinjen.
    sentences = split_sentences(text)
    running_word = 0
    contrast_figure_count = 0

    for s in sentences:
        stoks = tokenize(s)
        tokset = set(stoks)
        hit = False
        for a, b in LANG[lang]["contrast"]:
            if b is None:
                if a in tokset:
                    hit = True
                    break
            else:
                if a in tokset and b in tokset and stoks.index(a) < stoks.index(b):
                    hit = True
                    break

        if hit:
            tt = LEAD_IN_SECONDS + (running_word / WORDS_PER_SECOND)
            for j, hit_sound in enumerate(contrast_hits):
                indicator_events.append((tt + j * 0.160, hit_sound * 0.34))
            contrast_figure_count += 1

        running_word += len(stoks)

    # Ordklocka: ett tick efter varje fullbordat 30-ordsblock. Klicken har
    # samma tempo mellan texter eftersom hela tidslinjen använder 200 ord/s.
    for marker_word in range(WORDS_PER_TICK, total_words + 1, WORDS_PER_TICK):
        tt = LEAD_IN_SECONDS + (marker_word / WORDS_PER_SECOND)
        time_marker_events.append((tt, time_tick * TIME_MARKER_GAIN))

    # Rendera
    end = canvas_seconds
    indicator_y = np.zeros(int(end * SR), dtype=np.float32)
    time_marker_y = np.zeros(int(end * SR), dtype=np.float32)

    for ts, s in sorted(indicator_events, key=lambda x: x[0]):
        i = int(ts * SR)
        j = i + len(s)
        if j > len(indicator_y):
            indicator_y = np.pad(indicator_y, (0, j - len(indicator_y)))
        indicator_y[i:j] += s

    for ts, s in time_marker_events:
        i = int(ts * SR)
        j = i + len(s)
        if j > len(time_marker_y):
            time_marker_y = np.pad(time_marker_y, (0, j - len(time_marker_y)))
        time_marker_y[i:j] += s

    # Evidensviktad nivå: låg indexnivå ska faktiskt låta lägre. v2 lyfte alla
    # filer till samma toppnivå, vilket gjorde kontrolltexter onödigt påträngande.
    indicator_y *= 0.32 + 0.78 * fs.anomaly_index

    # Ordklockans klang och tempo är identiska; antalet tick följer ordantalet.
    y = indicator_y + time_marker_y

    # Mastering: lägg headroom utan att normalisera svaga filer uppåt.
    peak = float(np.max(np.abs(y))) if len(y) else 0.0
    target_peak = 0.16 + 0.58 * fs.anomaly_index
    if peak > target_peak > 1e-9:
        y *= target_peak / peak

    y = np.clip(y, -0.82, 0.82)
    write_wav(output, y)

    return {
        "wav": str(output),
        "seconds": len(y) / SR,
        "events": len(indicator_events) + len(time_marker_events),
        "indicator_events": len(indicator_events),
        "word_clock_event_count": len(time_marker_events),
        "audible_coordination_count": audible_coordination_count,
        "audible_pair_count": audible_pair_count,
        "audible_triad_count": audible_triad_count,
        "suppressed_clause_count": suppressed_clause_count,
        "suppressed_uncertain_count": suppressed_uncertain_count,
        "suppressed_context_count": suppressed_context_count,
        "repeated_attenuated_count": repeated_attenuated_count,
        "contrast_figure_count": contrast_figure_count,
        "density_alert_count": density_alert_count,
        "jackpot_count": jackpot_count,
        "extreme_wow_count": jackpot_count,
        "density_pair_weight": DENSITY_PAIR_WEIGHT,
        "density_triad_weight": DENSITY_TRIAD_WEIGHT,
        "density_clause_penalty": DENSITY_CLAUSE_PENALTY,
        "wow_density_threshold": WOW_DENSITY_THRESHOLD,
        "words_per_tick": WORDS_PER_TICK,
        "words_per_second": WORDS_PER_SECOND,
        "word_clock_interval_seconds": TIME_MARKER_INTERVAL,
        "word_clock_gain": TIME_MARKER_GAIN,
        "phrase_pair_interval_seconds": PHRASE_PAIR_INTERVAL,
        "content_seconds": content_seconds,
        "timeline_seconds": canvas_seconds,
        "anomaly_index": fs.anomaly_index,
        "band": band(fs.anomaly_index),
    }


# ---------------------------------------------------------------------------
# FILER OCH EXPORT
# ---------------------------------------------------------------------------

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_csv(path: Path, fs: FeatureSet):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["feature", "value"])
        for k, v in asdict(fs).items():
            w.writerow([k, v])


def build_report(text: str, lang: str) -> dict:
    fs, coords = extract_features(text, lang)
    return {
        "band": band(fs.anomaly_index),
        "reasons": explain(fs),
        "features": asdict(fs),
        "coordination_examples": coords[:100],
        "warning": (
            "Resultatet visar stilistiska signaler och avvikelsemönster. "
            "Det är inte bevis för att AI har använts och fastställer inte författarskap."
        ),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Förklarbar textanalys och sonifiering av stilistiska AI-relaterade signaler."
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_analyze = sub.add_parser("analyze", help="Analysera en text.")
    p_analyze.add_argument("input", type=Path)
    p_analyze.add_argument("--lang", choices=["sv", "en"], default="sv")
    p_analyze.add_argument("--json", type=Path)
    p_analyze.add_argument("--csv", type=Path)

    p_compare = sub.add_parser("compare", help="Jämför en aktuell text mot tidigare texter.")
    p_compare.add_argument("suspect", type=Path)
    p_compare.add_argument("baseline", nargs="+", type=Path)
    p_compare.add_argument("--lang", choices=["sv", "en"], default="sv")
    p_compare.add_argument("--json", type=Path)

    p_sonify = sub.add_parser("sonify", help="Skapa en WAV-sonifiering av texten.")
    p_sonify.add_argument("input", type=Path)
    p_sonify.add_argument("output", type=Path)
    p_sonify.add_argument("--lang", choices=["sv", "en"], default="sv")

    p_full = sub.add_parser("full", help="Kör analys och sonifiering i samma steg.")
    p_full.add_argument("input", type=Path)
    p_full.add_argument("--lang", choices=["sv", "en"], default="sv")
    p_full.add_argument("--json", type=Path)
    p_full.add_argument("--csv", type=Path)
    p_full.add_argument("--wav", type=Path, required=True)

    p_soundbank = sub.add_parser(
        "soundbank",
        help="Exportera flipper-/tivoliljuden som separata WAV-filer."
    )
    p_soundbank.add_argument("output_dir", type=Path)

    args = ap.parse_args()

    if args.cmd == "analyze":
        text = load_text(args.input)
        report = build_report(text, args.lang)
        print(json.dumps(report, ensure_ascii=False, indent=2))

        fs, _ = extract_features(text, args.lang)

        if args.json:
            args.json.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        if args.csv:
            write_csv(args.csv, fs)

    elif args.cmd == "compare":
        suspect_text = load_text(args.suspect)
        suspect_fs, suspect_coords = extract_features(suspect_text, args.lang)

        baseline_fs = [
            extract_features(load_text(p), args.lang)[0]
            for p in args.baseline
        ]

        payload = {
            "band": band(suspect_fs.anomaly_index),
            "reasons": explain(suspect_fs),
            "features": asdict(suspect_fs),
            "coordination_examples": suspect_coords[:100],
            "baseline_comparison": compare_against_baseline(
                suspect_fs, baseline_fs
            ),
            "warning": (
                "Jämförelsen visar stilistisk avvikelse från baslinjen. "
                "Den fastställer inte AI-användning."
            ),
        }

        print(json.dumps(payload, ensure_ascii=False, indent=2))

        if args.json:
            args.json.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

    elif args.cmd == "sonify":
        text = load_text(args.input)
        info = sonify(text, args.lang, args.output)
        print(json.dumps(info, ensure_ascii=False, indent=2))

    elif args.cmd == "full":
        text = load_text(args.input)
        report = build_report(text, args.lang)
        fs, _ = extract_features(text, args.lang)
        audio = sonify(text, args.lang, args.wav)

        report["sonification"] = audio
        print(json.dumps(report, ensure_ascii=False, indent=2))

        if args.json:
            args.json.write_text(
                json.dumps(report, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )

        if args.csv:
            write_csv(args.csv, fs)

    elif args.cmd == "soundbank":
        info = export_soundbank(args.output_dir)
        print(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
