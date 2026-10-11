# Textklang

En svensk webbapp för att **lyssna på textens struktur**. Klistra in text eller
ladda upp TXT/DOCX, hör ljudbilden och följ signalerna längs en interaktiv tidslinje.
Byggd från det bifogade paketet **AI Style Triage v2.10**.

Appen identifierar stilistiska mönster. Den fastställer inte AI-användning,
författarskap eller fusk. Stilindex är ett heuristiskt mått, **inte en sannolikhet**.
Inga externa AI-modeller, API-nycklar eller databaser behövs.

## Funktioner

- Svensk regelbaserad analys av fraspar, treled och retoriska kontraster.
- Originalmotorns ordklocka och klusterljud, med en synkroniserad tidslinje.
- Uppspelning i 1×, 0,5× eller 0,25×; klicka i tidslinjen för att hoppa.
- Ljudguide med sex provlyssningsbara signaler.
- Nedladdning av WAV, JSON-rapport och CSV med samtliga analysmått.
- UTF-8 TXT samt DOCX med stycken och tabeller i dokumentordning.
- Mobilanpassad sida utan externa typsnitt, statistikverktyg eller CDN.

## Kör lokalt

Python 3.12 rekommenderas. Från projektkatalogen:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt -c requirements.lock
.venv/bin/python -m uvicorn app:app --host 0.0.0.0 --port 8000 --no-access-log
```

Öppna port 8000 i din egen lokala utvecklingsmiljö. På Windows använder du
`.venv\Scripts\python.exe` i stället. Hälsokontroll: `GET /api/health`.

```sh
.venv/bin/python -m unittest discover -s tests -v
node --check static/app.js
```

`requirements.lock` låser även transitiva beroenden. GitHub Actions kör testerna.

## Publicera som hemsida

Projektet innehåller `Dockerfile` och en Render Blueprint (`render.yaml`).
GitHub Pages räcker inte eftersom analysen körs i Python på servern.

1. Logga in på [Render](https://render.com) och anslut ditt GitHub-konto.
2. Välj **New → Blueprint**, välj `davidhedengren/anticheat` och branch `main`.
3. Granska tjänsten `textklang` och skapa den. Render bygger Docker-imagen och
   ger tjänsten en HTTPS-adress. Inga miljövariabler eller hemligheter behövs.
4. Kontrollera `/api/health` och analysera exempeltexten på den nya hemsidan.

Blueprinten väljer gratisplanen. Tillgänglighet och villkor avgörs av Render;
vilande tjänster kan behöva tid för första starten. Ändra plan om du behöver
ständig tillgänglighet. En publik server har inga användarkonton i denna version.
För skolövergripande användning bör åtkomst begränsas via er driftplattform.

Alternativt, på en Docker-värd:

```sh
docker build -t textklang .
docker run --rm -p 8000:8000 textklang
```

Servern lyssnar på `$PORT`, annars 8000. Lägg HTTPS framför tjänsten när den
publiceras. Render sköter detta. Driftsättning till ett externt konto och kontroll
av dess publika adress är separata steg från lokal validering.

## Datahantering och gränser

Uppladdningar behandlas på servern, inte i en extern AI-tjänst. Appen sparar inga
texter, rapporter eller analysregister. WAV skapas i en tillfällig katalog som
raderas efter svaret. Webbläsaren behåller resultatet i minnet tills sidan stängs
eller laddas om. Server/hostingplattform kan ha egna åtkomstloggar och policyer.
Använd anonymiserade texter där det är möjligt.

Gränser: 2 MB per fil, 12 000 ord och 120 000 tecken per text. Två analyser kan
köras samtidigt per serverprocess; övriga får ett tydligt försök-igen-svar.
DOCX med för stor uppackad storlek avvisas. Bilder, fotnoter, sidhuvuden och
ändringsspår tolkas inte. PDF/OCR stöds inte.

## Motor och tidslinje

`vendor/engine.py` är originalprogrammets oförändrade Pythonfil. Dess SHA-256:

```
b1320f7c50087655a8c1a786be8ac769d65e66a0bdf3d89f6f053acfa915d1b2
```

`sonification.py` observerar motorns faktiska ljudschemaläggning via Python AST.
Den returnerar varje ljudhändelses tid, ordposition, typ och varaktighet, utan
att kopiera eller ändra klassningsregler, vikter eller tidsregler. Treled består
av tre deltoner och kontraster av två; tidslinjen visar även dessa delhändelser.
Ordpositionerna är motorns **nollbaserade** positioner, och kontrastljud placeras
vid meningens början enligt originalmotorn.

Adaptern korrigerar ett reproducerat renderingsfel i v2.10: om ett sent ljud
sträcker sig förbi den planerade ljudlängden får indikator- och ordklocksspåret
olika längd, och originalet kraschar vid addition. Adaptern fyller det kortare
spåret med tystnad före mixning. Analysmåtten och signalernas tider ändras inte.
Tester jämför WAV byte för byte på texter där originalet kan rendera och testar
separat korta klustertexter som tidigare kraschade.

Tidsregler: 0,45 sekunders inledning, 200 ord/sekund, ett tick varje 30 ord.
Ljudbilden är en sonifiering, inte uppläsning. Långsam uppspelning gör täta
händelser lättare att följa och ändrar enbart lyssningstempot.

Se [ljudguiden](docs/LJUDGUIDE_v2_10.md) och [materialanalysen](docs/MATERIALANALYS.md).
Uppladdade exempel-WAV och DOCX-förklaringen publiceras inte i repot; ljudbanken
kommer från projektpaketet. Ingen licens har lagts till för det tillhandahållna
materialet eftersom dess licens inte var angiven.
