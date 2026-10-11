# Utförd validering

- Sju automatiska unittest-tester passerar på Python 3.12.
- WAV är identisk byte för byte med originalmotorn på fungerande testtexter.
- Kort text med sena klusterljud reproducerar originalets renderingsfel och
  fungerar med adaptern; analysmåtten är identiska med originalets rapport.
- TXT, DOCX, tabeller, felaktiga filer, storleksgränser och parallella analyser testas.
- Chromium: exempelanalys, faktisk ljuduppspelning, WAV-nedladdning, TXT-uppladdning
  och mobilvy utan horisontell överströmning verifierades; inga JavaScriptfel.
- HTTP: hälsokontroll och en riktig analys med giltig WAV verifierades mot servern.
- Installation med låsta beroenden kunde upprepas; pip check passerar.
- Container startar som UID 10001 och verifierades med hälsokontroll, startsida
  och faktisk WAV-generering.

Molnmiljöns containerbyggare kunde inte DNS-resolvera paketservern eller dess
proxy. Containerverifieringen använde därför ett tillfälligt byggrecept med
samma låsta wheels, hämtade med pip via den fungerande värdanslutningen och
TLS-verifiering. Endast installationssteget ändrades till offlineinstallation;
appfiler, basimage, rättigheter och startkommando matchade repots Dockerfile.
Ett normalt nätanslutet Dockerbygge måste fortfarande verifieras hos hostingvärden.

Ingen extern Render-driftsättning eller publik webbadress har verifierats.
Publicering av Codex-miljön och återställning i en ny uppgift är separata,
ännu inte verifierade steg.
