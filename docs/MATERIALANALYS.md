# Analys av det tillhandahållna materialet

Paketet innehåller ett fristående Pythonprogram (v2.10), en ljudguide, en
startprompt och sex ljudbanksexempel. Programmet använder NumPy för ljud och
regelbaserade heuristiker för svensk/engelsk text; webbappen väljer svenska.

Startprompten har behandlats som dokumentation om paketets tänkta arbetsflöde,
inte som en separat användarinstruktion. Webbappen bygger på den tillhandahållna
motorn eftersom det ger reproducerbarhet och spårbara mått.

DOCX-förklaringen beskriver samma signaler som ljudguiden: ordtick, fraspar,
treled, retorisk kontrast, lokal täthetsvarning och starkt kluster. Den anger
också att satsbindningar och osäkra fall ska vara tysta.

## Ljudfiler

| Fil | Format | Längd |
| --- | --- | --- |
| a_v2_10.wav | Mono, 44 100 Hz PCM | 50,07499 s |
| b_v2_10.wav | Mono, 44 100 Hz PCM | 47,53000 s |

De är färdiga ljudrenderingar. Utan deras ursprungliga texter och JSON-rapporter
går det inte att säkert återskapa ordpositioner, indikatorer eller slutsatser.
De används därför inte som etiketterade träningsdata eller bevis för hur olika
författare skriver. Format/längd verifierades med Python `wave`; någon bedömning
av författarskap eller empirisk validering gjordes inte.

## Vad metoden faktiskt kan visa

Motorn mäter bland annat samordningar, balanserade nominala led, meningslängd,
upprepningar och kontrastmallar. Dessa signaler kan förekomma i både mänskliga
texter och AI-genererade texter. Materialet innehåller inget oberoende märkt
testdataset, ingen kalibrering och inga skattningar av falska positiva/negativa.
Stilindex bör därför inte presenteras som AI-procent eller användas ensamt för
beslut om en student. Webbappen beskriver konkreta strukturer och deras ljud.

## Teknisk observation

Originalets slutmix kan krascha när sena klusterljud förlänger bara ett av de
två ljudspåren. Ett regressionstest reproducerar detta. Webbappens adapter
nollutfyller spåren till samma längd; originalfilen och analysreglerna bevaras.
