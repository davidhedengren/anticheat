# Ljudguide för AI Style Triage v2.10

## Ordklockan

Version 2.10 använder en textbunden ordklocka. Ett lågt tick spelas efter varje
30 ord. Hela tidslinjen löper med 200 ord per sekund, vilket innebär att klicken
kommer med 0,15 sekunders mellanrum.

Analysljuden placeras med samma omvandling:

```text
tid = 0,45 sekunder + ordposition / 200
```

Om ett analysljud hörs mitt emellan två tick ligger konstruktionen ungefär 15
ord efter det föregående 30-ordsticket. Ljudfilens längd följer textens ordantal
och är därför inte densamma för olika texter.

## Ljudtabell

| Ljud | Betydelse | Viktigaste trigger | Vad lyssnaren hör |
| --- | --- | --- | --- |
| Ett lågt tick | Textens grundtempo | Efter vart 30:e ord | Hur långt textflödet har kommit; ticket är inte en punkt |
| Två korta flippertoner, låg–hög | Tydligt fraspar kring `och/eller` | Två korta, balanserade och tydligt nominala led | En avgränsad parbildning |
| Tre stigande flipperklockor | Tydligt treled, ungefär A, B och C | Tre korta och balanserade nominala led | En starkare liststruktur än ett vanligt par |
| Tvåtons tivolisignal | Retorisk kontrast | `inte ... utan`, `inte ... enbart` eller `snarare` | En kontrastmall, inte ett täthetslarm |
| Två låga mekaniska larmpulser | Flera säkra strukturer ligger tätt | Lokal strukturpoäng når minst 4,0 inom 180 ord | Ett kluster; treled bidrar mer än vanliga par och satsbindningar dämpar |
| Långt wow-svep med brusfinal | Särskilt starkt strukturkluster | Lokal strukturpoäng minst **5,5**, globalt index minst 0,50 och minst 180 ord sedan föregående wow | Den starkaste klustersignalen; i v2.10 kan den återkomma oftare |
| Tyst | Satsbindning, verbfras, satskedja eller osäkert fall | Bland annat meningsinledande `och`, minst fem `och` i samma mening eller ett osäkert grammatiskt fall | Programmet undviker att göra rå mängd `och` till en signal |

De viktigaste täthetsbidragen är `2,0` för ett säkert treled, `0,5` för ett
säkert par och `−0,12` för en satslik samordning, därefter justerat för
säkerhet och upprepning. Tabellen ovan räcker för normal lyssning; de fulla
värdena finns i JSON-rapporten.

## Rapportmått

Rapporten skiljer nu mellan `and_count`/`and_rate` och
`or_count`/`or_rate`. För svensk text motsvarar dessa `och` respektive `eller`.
Den redovisar också meningsinledande `och`, meningar med minst fem `och` och
långa meningar med minst tre `och`. Dessa mått gör satskedjefiltret granskningsbart.

## Exempel på ordklockan

- Tick 1: 30 ord har passerat.
- Tick 5: 150 ord har passerat.
- Tick 10: 300 ord har passerat.
- Flera flipperljud mellan tick 10 och 20 betyder flera tydliga strukturer i
  textavsnittet mellan ungefär ord 300 och 600.

## Ljudbank

- `00_ordklocka_tick_var_30e_ord.wav`
- `01_fraspar_flipper_lag_hog.wav`
- `02_treled_flipperklockor.wav`
- `03_tathetsvarning_mekaniskt_dubbellarm.wav`
- `04_kontrast_tivolisignal.wav`
- `05_extremkluster_wow_svep.wav`

## Två ljudfamiljer

- **Grundhändelser:** fraspar, treled och kontrast är korta, avgränsade och
  melodiska. De talar om *vilken konstruktion* som just hittades.
- **Täthetshändelser:** dubbellarmet och wow-svepet är längre och har annan
  klang. De talar om att flera konstruktioner ligger ovanligt tätt, inte om en
  ny enskild parbildning eller kontrast.

Banken kan återskapas med:

```bash
python ai_style_triage_v2_10.py soundbank ljudbank
```

## Viktig begränsning

Den grammatiska klassningen är en transparent approximation, inte en full
svensk syntaktisk parser. Programmet prioriterar hög precision i ljudbilden och
kan därför missa riktiga fraspar. Resultatet visar stilistiska signaler och
avvikelsemönster; det fastställer inte författarskap och bevisar inte att AI har
använts.
