# TerraCycle — stadiul proiectului și planul de lucru

Scris pe 13 noiembrie 2026. Planul de date a fost actualizat pe 14 noiembrie (secțiunile 3.4, 4.C, 4.G, 4.I, 4.J și 5). Termene: sâmbătă 14 noiembrie, ora 12:00 (aplicația rulează pe telefonul de demo) și duminică 15 noiembrie, ora 12:00 (bucla completă pe date reale).

Cuprins:

1. [Pe scurt](#1-pe-scurt)
2. [Explicat simplu](#2-explicat-simplu)
3. [Stadiul tehnic](#3-stadiul-tehnic)
4. [Ce rămâne de făcut și cum](#4-ce-rămâne-de-făcut-și-cum)
5. [Planul pentru parcele de orice mărime](#5-planul-pentru-parcele-de-orice-mărime)
6. [Programul de mâine](#6-programul-de-mâine)
7. [Riscuri pentru demo](#7-riscuri-pentru-demo)
8. [Cum pornești totul](#8-cum-pornești-totul)
9. [Decizii pe care le așteptăm de la echipă](#9-decizii-pe-care-le-așteptăm-de-la-echipă)

---

## 1. Pe scurt

Stadiul la 14 noiembrie 2026.

TerraCycle este o aplicație de telefon în care un fermier pune o întrebare despre pământul lui și primește un răspuns direct. Întrebarea principală este „ce pun la anul?”, adică rotația culturilor.

**Cel mai important lucru de știut:** din datele NASA, aplicația folosește acum o singură sursă, NASA POWER (vremea zonei). Recomandarea de rotație în sine nu vine încă din date NASA, ci dintr-un tabel provizoriu de reguli. Celelalte surse NASA sunt descărcate pentru toate cele patru parcele (14 noiembrie), dar serverul nu le citește încă.

### 1.1 Cum funcționează acum

1. Fermierul deschide aplicația pe ecranul **Ask**. Vede un titlu despre vremea din zonă („It has been dry in your area lately.”) și două casete: ploaia din ultimele 30 de zile și apa din sol.
2. Scrie o întrebare sau atinge una sugerată. Serverul recunoaște două feluri de întrebări, după cuvinte-cheie: „ce plantez” și „cum îi merge parcelei”.
3. Dacă îi lipsește ceva, asistentul întreabă, cu răspunsuri la o atingere: pe care parcelă, apoi ce contează mai mult (apă, sol sau venit).
4. Primește o propoziție („Plant peas on Valea Mare.”) și un card cu planul pe trei ani, cel mult două motive și ce să evite.
5. „Why?” explică alegerea. Pentru prioritatea „apă”, arată un grafic cu ploaia din iulie din ultimii 10 ani, din NASA POWER.
6. „What can't you see?” spune ce nu se vede din spațiu: sol tasat, boli și dăunători, drenuri înfundate.

Aplicația nu calculează nimic singură. Trimite întrebarea la server și desenează răspunsul primit.

### 1.2 Ce primește fermierul acum

| Ce | Unde în aplicație | Pe ce se bazează |
|---|---|---|
| Starea vremii din zonă, la deschidere | Ask | NASA POWER |
| Recomandare de rotație pe trei ani, după prioritatea lui | Ask | Tabel provizoriu de reguli + istoricul culturilor (inventat) |
| Explicația recomandării | Ask, „Why?” | NASA POWER pentru „apă”; reguli generale pentru „sol” și „venit” |
| Harta parcelelor pe imagine din satelit, cu suprafața fiecăreia | My land | Contururile reale desenate de echipă; fundal Esri |
| Trei grafice despre zonă: ploaia pe an, temperatura verii, apa din sol | Data | NASA POWER |
| Lista „ce știu și ce nu știu despre pământul tău” | Data | Scrisă de noi, cu data ultimei zile de date |
| Întrebările puse până acum | History | Păstrate pe telefon |
| Răspunsul citit cu voce tare | Ask | Vocea telefonului |

Ce **nu** primește încă: starea culturii pe parcela lui. La întrebarea „cum îi merge parcelei”, asistentul răspunde „I don't have satellite readings for … yet”, iar pe hartă toate parcelele apar cu „No satellite reading yet”.

### 1.3 Datele NASA: ce e folosit și cum

**Folosit acum în aplicație: NASA POWER.** Date zilnice din 1 ianuarie 2001 până acum două-trei zile, pentru un punct din mijlocul parcelelor. Sunt estimări de model pe o grilă de circa 50 km, deci aplicația le etichetează peste tot ca „Estimate for your area”. „De obicei” înseamnă mereu media anilor 2001–2020.

| Parametru | Ce vede fermierul | Cum se calculează |
|---|---|---|
| `PRECTOTCORR` (ploaie) | Caseta „Rain in your area, 30 days” și titlul de pe Ask | Suma ultimelor 30 de zile față de media acelorași 30 de zile din 2001–2020. Sub 75% apare „Less than usual” |
| `PRECTOTCORR` | Graficul „Rain per year” din Data | Suma pe an, ultimii 10 ani; ultimul an față de medie, în procente |
| `PRECTOTCORR` | Graficul din „Why?” (prioritatea „apă”) | Ploaia din iulie; media ultimilor 5 ani față de media 2001–2020 |
| `T2M_MAX`, `T2M_MIN` (temperatură) | Graficul „Average temperature, June to August” | Media dintre maxime și minime pe iunie–august, față de medie, în °C |
| `GWETROOT` (apa din zona rădăcinilor) | Caseta „Water in the soil”: Low, Normal sau High | Media ultimelor 7 zile, așezată printre aceleași 7 zile din cei 20 de ani; treimea de jos e „Low” |
| `GWETROOT` | Graficul „Water in the root zone” | Media pe lună, anul acesta față de medie; propoziția judecă iulie–septembrie |

Codul: descărcarea în `backend/power.py`, calculele și propozițiile în `backend/analysis.py`.

**Descărcat, dar încă nefolosit de aplicație:**

- NASA POWER pe punctul fiecărei parcele, 2001–2020, adunat pe săptămâni, cu trei parametri în plus (punct de rouă, vânt, radiație solară). Este în `backend/data/baked/<id>/profile.json`. E materia primă pentru rejucarea anilor și calendarul sezonului.
- SoilGrids (nu e NASA): textura solului, pH și carbon organic.

**Descărcat prin Earth Engine pe 14 noiembrie, încă nefolosit de aplicație** (toate cu `status: ok` în `profile.json`):

| Sursă NASA | La ce va folosi | Eticheta |
|---|---|---|
| HLS (Landsat + Sentinel-2, 30 m) | Cât de verde e parcela față de alți ani: starea parcelei | pe parcelă |
| MODIS NDVI (250 m) | Cât de verde a fost zona în ultimii 20 de ani | pe zonă |
| SMAP (~9 km) | Apa din sol, din 2015 | pe zonă |
| GPM IMERG (~10 km) | Zilele cu ploi torențiale | pe zonă |
| NASADEM (30 m) | Panta și locurile joase din parcelă | pe parcelă |

Pe lângă NASA: Sentinel-2 (ESA, 10 m), pentru harta zonelor din interiorul parcelei. Detaliile sunt în 4.C și în `README.md`.

### 1.4 Ce e făcut și unde

| Parte | Unde | Stadiu |
|---|---|---|
| Ecranele Ask, My land, Data, History | `app/src/app/` | Merg în emulator, pe serverul real |
| Conversația pe telefon și istoricul | `app/src/conversation.tsx` | Merge |
| Harta (Leaflet) și graficele | `app/src/components/` | Merg |
| Legătura cu serverul | `app/src/api.ts` | Merge; singurul loc care alege între server și date de test |
| Datele de test pentru modul fără server | `app/src/mock/` | Învechite: parcele vechi, texte în română |
| Adresele serverului | `backend/main.py` | Merg |
| Parcelele și tabelul de culturi | `backend/store.py`, `backend/fields.json` | Contururi reale; nume, culturi și istoric inventate; tabel provizoriu |
| Vremea și calculele | `backend/power.py`, `backend/analysis.py` | Merg, pe date reale |
| Conversația și rotația | `backend/engine.py` | Merge; rotația e pe reguli provizorii |
| Descărcarea tuturor surselor | `backend/field_pull.py` | Rulat pe toate sursele și toate parcelele; rezultatul e în `backend/data/baked/` |
| Tabelul de culturi cu surse | `backend/crops.json`, `backend/SOURCES.md`, `backend/MISSING.md`, `backend/test_crops.py` | Fiecare valoare are sursă, loc în sursă și stare („verificat” sau „de_confirmat”). 15 surse; ce n-are sursă e gol și listat în `MISSING.md`. Un test pică dacă apare o cifră fără sursă. Motorul nu îl folosește încă |
| AI-ul local | `ai/`, `backend/llm.py`, `backend/knowledge.py`, `backend/llm_prompts.py` | Set de antrenare, corpus de literatură (FAO-56, FAO-66, articole), script de antrenare și arhivă pentru Colab: gata și probate pe rulări scurte. Modelul încă nu e antrenat. Serverul are legătura scrisă, probată doar cu modelul simulat. Detalii în `ai/README.md` |
| Git | depozitul `TerraCycle` | Un commit, urcat pe GitHub; schimbările din 14 noiembrie sunt necomise |

### 1.5 Ce mai trebuie făcut

În ordinea în care se deblochează. Detaliile fiecărui punct sunt în secțiunea 4.

1. ~~Autentificarea Earth Engine și rularea `field_pull.py`~~ (4.C). Făcut pe 14 noiembrie.
2. **Serverul citește `profile.json`**: starea reală a parcelelor din HLS, graficul „How green the crop is”, nivelurile de parcelă după mărime (secțiunea 5).
3. **Motorul de rotație cu rejucarea anilor** (4.D): miezul proiectului. Abia aici recomandarea începe să vină din date NASA. Cere un tabel de culturi cu surse.
4. **Calendarul sezonului** (4.E).
5. **Build pentru telefon** (4.A) și datele de test aduse la zi (4.B).
6. **AI-ul local** pentru înțelegerea întrebărilor libere (4.F). Acum sunt doar cuvinte-cheie.
7. Dacă rămâne timp: harta zonelor (4.I), solul și corecturile fermierului (4.G), scenarii (4.H), panta (4.J).

Lipsesc de la echipă: culturile reale de pe cele patru parcele și valorile pentru tabelul de culturi (secțiunea 9).

---

## 2. Explicat simplu

*Partea aceasta e scrisă ca pentru cineva de liceu care n-a văzut proiectul.*

### Ce face aplicația

Un fermier trebuie să hotărască în fiecare an ce seamănă pe fiecare bucată de pământ. Dacă pune aceeași plantă la nesfârșit, pământul sărăcește și bolile se adună. Dacă schimbă plantele cu cap (asta se numește **rotație**), pământul rămâne sănătos. Aplicația îl ajută să aleagă: îi spune ce să pună la anul și de ce.

### De unde știe aplicația ceva despre pământul lui

Din trei locuri:

1. **Sateliții NASA** fotografiază Pământul în fiecare zi. Din poze se poate măsura cât de verde e o cultură. O cultură verde e de obicei sănătoasă.
2. **Modelele de vreme NASA** știu cât a plouat și cât de cald a fost în fiecare zi, din 2001 încoace.
3. **Fermierul** spune ce a cultivat și răspunde la întrebări scurte.

### De ce contează mărimea parcelei

O poză din satelit e făcută din pătrățele, ca un mozaic. La sateliții pe care îi folosim, un pătrățel are 30 de metri pe 30 de metri, cam cât două terenuri de baschet. Tot ce e într-un pătrățel se vede ca o singură culoare.

- Dacă parcela e mare, încap în ea zeci de pătrățele întregi. Putem spune cât de verde e.
- Dacă parcela e o grădină de câțiva ari, e mai mică decât un singur pătrățel. Culoarea lui amestecă grădina cu drumul și cu grădina vecinului. Nu putem spune nimic sigur despre ea.

Vremea e altceva: un „pătrățel” de vreme are cam 50 de kilometri. Ploaia și temperatura sunt aceleași pentru tot satul, deci sunt la fel de bune pentru o grădină mică și pentru o fermă mare.

De aceea aplicația îi ajută pe toți, dar pe căi diferite. La parcelele mari se uită din satelit. La cele mici folosește vremea din zonă și îl întreabă pe fermier ce vede cu ochii lui.

### Ce înseamnă „de obicei”

Când aplicația spune „mai puțină ploaie decât de obicei”, compară cu media anilor 2001–2020 pentru același loc și aceeași perioadă din an. Nu e o părere, e o scădere între două numere.

### Ce face și ce nu face inteligența artificială

AI-ul din aplicație are o singură treabă: să înțeleagă întrebarea, oricum ar fi scrisă. Răspunsul îl calculează un program obișnuit, din date. Așa AI-ul nu poate inventa cifre.

### Regula de onestitate

Aplicația spune ce vede, nu ce ghicește. „Cultura e mai puțin verde” e ceva ce se vede. „Cultura e bolnavă” e o ghicitoare, pentru că din spațiu nu se văd dăunătorii sau pământul tasat. Când nu știe, aplicația spune că nu știe și îl întreabă pe fermier.

---

## 3. Stadiul tehnic

### 3.1 Arhitectură

```
Telefon (Expo / React Native)                Laptop
┌───────────────────────────┐   HTTP/JSON   ┌──────────────────────────────────────┐
│ Ask · My land · Data      │ ────────────► │ FastAPI (backend/main.py)            │
│ api.ts = singurul fișier  │               │  ├─ store.py     parcele + tabel culturi │
│ care știe de server       │ ◄──────────── │  ├─ power.py     NASA POWER + cache  │
└───────────────────────────┘               │  ├─ analysis.py  cifre și propoziții │
                                            │  └─ engine.py    conversația         │
                                            └──────────────────────────────────────┘
                                               ▲ NASA POWER (fără cont)
                                               ▲ Earth Engine (neconectat încă)
                                               ▲ Model de limbaj local (neexistent încă)
```

Aplicația nu calculează nimic și nu formulează nicio afirmație. Afișează textele și cifrele primite de la server. Dacă adresa serverului lipsește din `app/.env`, aplicația folosește datele de test din `app/src/mock/`.

### 3.2 Aplicația de telefon (`app/`)

Expo SDK 58, Expo Router, TypeScript, React Native 0.88, TanStack Query, react-native-svg, Leaflet într-un WebView pentru hartă.

| Ecran | Fișier | Ce face |
|---|---|---|
| Ask | `src/app/(tabs)/index.tsx` | Rezumatul de la deschidere, apoi conversația |
| My land | `src/app/(tabs)/land.tsx` | Hartă din satelit cu contururile, lista parcelelor, istoricul culturilor |
| Data | `src/app/(tabs)/data.tsx` | „What I know about your land” și analizele cu grafice |
| History | `src/app/history.tsx` | Întrebările vechi, păstrate pe telefon |

Alte fișiere importante: `src/api.ts` (comutatorul date de test / server), `src/conversation.tsx` (starea conversației, citirea cu voce tare), `src/theme.ts` (toate culorile și mărimile), `src/i18n.tsx` (toate textele interfeței, doar în engleză).

Limitări cunoscute:

- Butonul de microfon doar deschide tastatura; dictarea o face tastatura telefonului.
- Datele de test din `src/mock/` au încă parcelele vechi, inventate, și texte românești nefolosite.
- Rulează în Expo Go pe emulator. Nu există încă un build pentru telefon.

### 3.3 Serverul (`backend/`)

Python 3.12, FastAPI, mediu virtual în `backend/.venv`.

| Adresă | Ce întoarce | Sursa datelor |
|---|---|---|
| `GET /me` | Numele și regiunea utilizatorului | `fields.json` (valoare de test) |
| `GET /fields` | Parcelele ca GeoJSON, cu suprafața calculată | Contururi reale; cultura e de test |
| `GET /fields/{id}` | Istoricul culturilor | De test |
| `GET /overview` | Titlul și cele două casete de pe ecranul principal | NASA POWER |
| `GET /insights` | Lista „ce știu” și graficele din Data | NASA POWER |
| `POST /converse` | Un răspuns de conversație | Reguli + NASA POWER |

Formele exacte ale răspunsurilor sunt în `app/src/types.ts`.

### 3.4 Datele folosite acum

Două surse sunt conectate și descărcate: **NASA POWER** și **SoilGrids**. Restul surselor din planul de date (4.C) sunt descărcate în `backend/data/baked/`, dar aplicația nu le arată încă.

**NASA POWER**, comunitatea AG, date zilnice, din 1 ianuarie 2001. Serverul îl citește pentru un punct (mijlocul celor patru parcele, 44,231° N, 23,824° E); `field_pull.py` îl descarcă și pe punctul fiecărei parcele, pentru 2001–2020.

| Parametru POWER | Ce înseamnă | Folosit pentru |
|---|---|---|
| `T2M_MAX`, `T2M_MIN` | Temperatura maximă și minimă la 2 m, °C | Temperatura medie a verii; arșiță și îngheț în rejucare |
| `PRECTOTCORR` | Precipitații corectate, mm/zi | Ploaia pe an, pe iulie, pe ultimele 30 de zile |
| `GWETROOT` | Umezeala solului în zona rădăcinilor, 0–1 | Apa din sol |
| `T2MDEW`, `WS2M`, `ALLSKY_SFC_SW_DWN` | Punctul de rouă (°C), vântul la 2 m (m/s), radiația solară (MJ/m²/zi) | Descărcate, încă nefolosite: apa cerută de cultură (evapotranspirația de referință) în rejucare |

Meteorologia POWER provine din reanaliza MERRA-2 și din modelul GEOS, pe o grilă de aproximativ 0,5° × 0,625° (circa 50 km). Sunt estimări de model, nu măsurători la sol. Datele ajung cu două-trei zile întârziere. Răspunsul se păstrează pe disc 24 de ore în `backend/cache/`; fără internet, serverul folosește ultima copie.

**SoilGrids 2.0** (ISRIC, 250 m, fără cont): nisip, praf, argilă, pH și carbon organic pe primii 30 cm, pentru punctul fiecărei parcele. Sunt hărți prezise de un model din profile de sol, deci estimări pentru zonă. Valorile descărcate: sol argilos pe toate patru (45–47% argilă; „silty clay” la Dealul Viei și Lunca Jiului, „clay” la Valea Mare și Pădurea Veche), pH 6,6–6,8. Încă nu apar în aplicație.

### 3.5 Metodele de calcul

Perioada de referință („usual”) este 2001–2020 peste tot.

| Mărime | Definiție | Condiție de date | Prag pentru propoziție |
|---|---|---|---|
| Ploaie pe an | Suma zilnică pe anul calendaristic | Cel puțin 360 de zile valide | ±10% față de referință |
| Temperatura verii | Media lui (Tmax + Tmin)/2 pe iunie–august | Cel puțin 85 de zile | ±0,5 °C |
| Apa din sol, sezon | Media lunară `GWETROOT`, iulie–septembrie | Cel puțin 25 de zile pe lună | ±5% |
| Ploaia din ultimele 30 de zile | Suma față de aceeași fereastră din anii de referință | Cel puțin 27 de zile | Raport sub 0,75 sau peste 1,25 |
| Apa din sol, acum | Media pe 7 zile, rangul printre aceleași 7 zile din anii de referință | Cel puțin 5 zile | Treimea de jos = „Low”, de sus = „High” |
| Ploaia din iulie | Media ultimilor 5 ani față de referință | Cel puțin 29 de zile | ±10% |

Nu se face nicio afirmație de tendință („scade în timp”). Toate propozițiile compară o valoare cu media de referință, pentru că zece ani sunt prea puțini pentru o tendință credibilă.

Valori obținute pentru zona parcelelor:

- 2025: 541 mm de ploaie, față de 628 mm referință (−14%).
- Vara 2026: 26,2 °C, față de 24,35 °C referință (+1,9 °C).
- Iulie, media 2022–2026: 38 mm, față de 63 mm referință.
- Ultimele 30 de zile până la 10 noiembrie: 97 mm, față de 44 mm referință.

### 3.6 Motorul de rotație (provizoriu)

Fiecare cultură din tabel (`store.py`) are note de la 1 la 3 pentru nevoia de apă, beneficiul pentru sol și venit, o familie botanică și un interval minim de revenire. Scorul unei culturi pentru anul următor:

- prioritatea „apă”: (4 − nevoia de apă) × 2, plus 1 dacă se recoltează devreme;
- prioritatea „sol”: beneficiul pentru sol × 2, plus 1 dacă fixează azot;
- prioritatea „venit”: nota de venit × 2;
- minus 3 dacă e din aceeași familie cu cultura de anul trecut;
- plus 1 dacă familia nu apare în ultimii doi ani;
- exclusă dacă a fost cultivată mai recent decât intervalul ei minim.

Planul pe trei ani se obține aplicând regula de trei ori la rând.

**Notele din tabel sunt puse de noi, fără sursă.** Motorul nu folosește încă vremea. Un defect cunoscut: pe prioritatea „sol” propune mazăre, rapiță și soia după floarea-soarelui. Din câte știm, toate patru sunt gazde pentru putregaiul alb (*Sclerotinia sclerotiorum*); de verificat într-o sursă agronomică.

### 3.7 Regulile de onestitate

1. Aplicația spune ce se observă („less green”), nu un diagnostic.
2. Fiecare cifră e etichetată: măsurată pe parcelă sau estimată pe zonă.
3. O cauză apare doar ca „most likely”, urmată de o întrebare către fermier.
4. Orice răspuns despre o parcelă oferă „How do you know?”.
5. Când o dată lipsește, răspunsul este „nu am încă”, nu o presupunere.

### 3.8 Ce a fost verificat

- Verificarea de tipuri TypeScript trece.
- Toate adresele serverului au fost apelate direct, inclusiv conversația pe toate ramurile: rotație cu cele trei priorități, „Why?”, „What can't you see?”, schimbarea priorității, sesiune pierdută, text liber.
- În emulator, cu serverul real: ecranul principal, tabul Data, harta cu parcelele reale, primul pas al conversației.
- Neverificat în emulator cu serverul real: restul conversației, istoricul, detaliile unei parcele.
- Neverificat deloc: un telefon adevărat.

---

## 4. Ce rămâne de făcut și cum

Ordinea e cea în care lucrurile se deblochează unul pe altul. „Must” înseamnă că fără el demo-ul nu stă în picioare.

### A. Git și build pentru telefon — Must, primul lucru de mâine

- **Problema:** depozitul git are rădăcina în `Desktop`, nu în `TerraCycle`, și tot proiectul e nesalvat.
- **Cum:** `git init` în `TerraCycle`, un prim commit. De hotărât dacă se urcă pe GitHub.
- **Build:** `npx eas-cli@latest build -p android --profile preview` din `app/`. Cere un cont Expo și durează, deci se pornește devreme.
- **Atenție la adresa serverului:** variabilele `EXPO_PUBLIC_*` se scriu în aplicație la build. Două variante:
  - APK cu date de test (fără adresă): merge oriunde, dar arată parcelele vechi. Întâi trebuie aduse datele de test la zi (punctul B).
  - APK cu adresa laptopului din rețea: cere același Wi-Fi, portul 8000 deschis în firewall și, probabil, permisiune pentru HTTP necriptat în build (de verificat: Android o blochează implicit în build-urile de release).
- **Gata când:** APK-ul instalat pe telefonul de demo arată ecranele Ask și My land.

### B. Datele de test aduse la zi — Must pentru varianta fără server

- **Cum:** parcelele reale și textele noi copiate din `backend/` în `app/src/mock/`; textele românești șterse.
- **Gata când:** aplicația fără adresă de server arată aceleași parcele ca aplicația cu server.

### C. Datele: descărcate o singură dată cu `field_pull.py` — Must

- **Ideea:** toate sursele se descarcă o singură dată per parcelă, se adună pe săptămâni și se salvează în `backend/data/baked/<id parcelă>/profile.json`. Serverul și demo-ul citesc doar fișierele salvate, deci merg și fără internet. Răspunsurile brute rămân în `backend/cache/pull/`, așa că o a doua rulare cere doar ce lipsește.
- **Săptămânile:** intervale de 7 zile numărate de la 1 ianuarie, 52 pe an (ultima ia și zilele rămase).
- **Blocat de:** autentificarea Earth Engine, pe care o face proprietarul contului Google:
  ```
  cd backend
  .\.venv\Scripts\earthengine authenticate --auth_mode=localhost
  .\.venv\Scripts\python.exe field_pull.py
  ```
  Proiectul este `terracycle-514620`. POWER și SoilGrids nu cer cont și sunt deja descărcate.
- **Stadiu:** rulat pe 14 noiembrie pentru toate cele patru parcele; toate cele opt surse au `status: ok`. Ce a ieșit:
  - Pătrate curate numărate pe imagini reale: Sentinel-2 are 1093 (Valea Mare), 616 (Dealul Viei), 207 (Lunca Jiului), 1097 (Pădurea Veche); HLS are 114, 64, 20 și 118. Toate parcelele trec pragul de 10 și la HLS.
  - Sentinel-2 și HLS arată aceeași curbă a sezonului. Din ea se vede dacă anul a avut cultură de toamnă sau de primăvară.
  - Relief: toate parcelele sunt plate (pantă medie 1–2°, maximă 4,5°), niciun pătrat abrupt; trei pătrate joase la Pădurea Veche.
  - Harta zonelor: Valea Mare are 23 de pătrate de 10 m (din 1027) mai slabe în cel puțin jumătate din ani; celelalte parcele au cel mult unul.
  - IMERG, SMAP și POWER dau aceleași valori pentru toate patru: parcelele stau în același pătrat de grilă.

**Obligatoriu** (calendarul pe 20 de ani și rejucarea):

| Sursă | Colecție sau API | Perioadă | Ce intră în `profile.json` (pe săptămâni) | Eticheta |
|---|---|---|---|---|
| NASA POWER | API zilnic, fără cont | 2001–2020 | `tmax`, `tmax_peak`, `tmin`, `tmin_low`, `tdew`, `wind`, `sun`, `rain`, `soil_wetness` | zonă, ~50 km |
| MODIS NDVI | `MODIS/061/MOD13Q1`, banda `NDVI` × 0,0001, păstrate doar `SummaryQA` 0 și 1 | 2001–2020 | `ndvi_area`: media pătratelor de 250 m care ating parcela | zonă, 250 m |
| SMAP | `NASA/SMAP/SPL4SMGP/008`, banda `sm_rootzone` | 2015–2020 | `soil_moisture_rootzone` | zonă, ~9 km |
| GPM IMERG | `NASA/GPM_L3/IMERG_V07`, banda `precipitation` (mm/h, la 30 de minute, adunată pe zile) | 2001–2020 | `rain_day_max`, `heavy_rain_days` (zile cu cel puțin 20 mm) | zonă, ~10 km |
| NASADEM | `NASA/NASADEM_HGT/001`, banda `elevation`, panta cu `ee.Terrain.slope` | februarie 2000 | panta medie și maximă, altitudinea minimă și maximă; `relief.geojson` | parcelă, 30 m |
| SoilGrids | API ISRIC, fără cont | static | textură, pH, carbon organic, 0–30 cm | zonă, 250 m |

NASADEM înlocuiește SRTM brut (`USGS/SRTMGL1_003`): e aceeași misiune, reprocesată de NASA, cu mai puține goluri.

**Recomandat** (harta din interiorul parcelei și citirea parcelei):

| Sursă | Colecție | Perioadă | Ce produce | Eticheta |
|---|---|---|---|---|
| Sentinel-2 (Copernicus, ESA) | `COPERNICUS/S2_SR_HARMONIZED`, nori scoși cu banda `SCL` (păstrate clasele 4 și 5) | 2017–azi | `ndvi_field_10m` pe săptămâni, săptămânile cu sol gol pe an, `zones.geojson` | parcelă, 10 m, ESA |
| HLS (NASA) | `NASA/HLS/HLSL30/v002` și `NASA/HLS/HLSS30/v002`, nori scoși cu `Fmask` | 2013–azi | `ndvi_field_30m` pe săptămâni (pașii din 5.4) | parcelă, 30 m |

- **Harta zonelor** (`zones.geojson`): pentru fiecare sezon (aprilie–septembrie), fiecare pătrat de 10 m e comparat cu mediana parcelei din același an. Cultura se schimbă de la an la an, deci păstrăm doar diferența din interiorul parcelei, niciodată nivelul. Un pătrat e „mai slab” într-un an dacă stă cu peste 10% sub mediană; harta arată în câți ani s-a întâmplat.
- **Sol gol:** săptămânile în care NDVI-ul parcelei e sub 0,25. Intră în recomandarea de rotație (cultură de acoperire).
- **Relieful** (`relief.geojson`): pătratele de 30 m cu pantă de cel puțin 5° sunt marcate pentru risc de eroziune. Locurile joase (cele mai de jos 10% din diferența de nivel) se marchează doar dacă parcela are cel puțin 5 m diferență de nivel, fiindcă eroarea NASADEM pe verticală e de câțiva metri. „Risc de îngheț în locul jos” e o deducție, nu o măsurătoare: apare doar ca „most likely”.
- **Împărțirea rolurilor:** MODIS e doar pentru istoricul de 20 de ani al zonei; Sentinel-2 e pentru harta parcelei; HLS e citirea NASA a parcelei.

**Opțional:** FAO GAEZ, ca să scoatem din listă culturile nepotrivite zonei. Nu e în catalogul oficial Earth Engine, deci s-ar descărca separat de pe portalul FAO. Se face doar dacă rămâne timp.

**Nu folosim:** ECOSTRESS (treceri prea rare), GEDI (măsoară păduri), ERA5 și NLDAS/GLDAS (avem deja POWER), și toate sursele care acoperă doar SUA (USDA, SSURGO, CDL, PRISM, NAIP, NLCD, OpenET și celelalte).

Toate pragurile de mai sus (20 mm, 0,25, 5°, 5 m, 10%) sunt alegerea noastră și intră pe lista „de verificat cu un agronom”. Lista surselor, cu versiune și link, este în `README.md`.

- **Gata când:** `profile.json` are `status: ok` la toate sursele pentru toate parcelele, `/fields` întoarce o stare reală, iar tabul Data are graficul „How green the crop is”.

### D. Motorul de rotație cu „rejucarea” anilor — Must, miezul proiectului

- **Ideea:** pentru fiecare cultură candidată, verificăm în fiecare an din 2001–2025 dacă perioadele ei sensibile ar fi căzut pe vreme rea. Rezultatul: „în 18 din 25 de ani, orzul ar fi scăpat de arșiță”. Numărul de ani buni este și măsura de încredere.
- **Ce trebuie pentru fiecare cultură:** data semănatului, fereastra de înflorire, fereastra de umplere a bobului, pragul de arșiță, pragul de îngheț, coeficientul de consum de apă.
- **Calcule:**
  - arșiță: numărul de zile cu Tmax peste prag în fereastra de înflorire;
  - îngheț: zile cu Tmin sub prag după răsărire;
  - deficit de apă: ploaia minus apa cerută de cultură în fereastra sensibilă. Apa cerută = coeficientul culturii × evapotranspirația de referință, calculată cu formula Hargreaves–Samani din Tmax, Tmin și latitudine.
- **Surse de căutat pentru tabel:** FAO Irrigation and Drainage Paper 56 (coeficienți și stadii de cultură), baza de date FAO ECOCROP (cerințele culturilor), un ghid agronomic românesc pentru datele de semănat din Oltenia. Fiecare valoare din tabel își notează sursa.
- **În aplicație:** pe cardul de rotație, 25 de puncte (an bun / an rău) și un rând „de ce ajută solul”.
- **Gata când:** recomandarea se schimbă dacă schimbi parcela, prioritatea sau scenariul, iar „Why?” arată anii buni și răi.
- **Limită de spus deschis:** nu avem date de recoltă, deci pragurile nu pot fi validate local. Intră pe lista „de verificat cu un agronom”.

### E. Calendarul sezonului — Must

- **Ce e:** un card în Data, per parcelă: săptămânile sezonului pe orizontală, patru rânduri (temperatură, ploaie, apă în sol, verde), cu perioadele sensibile ale culturii marcate și cu avertizări.
- **Cum:** serverul agregă datele zilnice pe săptămâni și marchează abaterile față de aceeași săptămână din anii de referință. Aplicația desenează o bandă de celule colorate.
- **Depinde de:** tabelul de culturi din D (pentru perioadele sensibile); rândul „verde” depinde de C.

### F. AI-ul local — Must pentru poveste, dar cu plasă de siguranță

- **Rol:** transformă întrebarea liberă în patru câmpuri: intenție, parcelă, cultură, prioritate. Nu scrie răspunsuri.
- **Cum:** Ollama pe laptop, un model mic care încape în memoria plăcii video (RTX 3060; memoria exactă de verificat). Serverul îi cere un JSON cu schemă fixă. Dacă modelul nu răspunde în 3 secunde sau JSON-ul e invalid, se folosește potrivirea pe cuvinte care există deja.
- **Alegerea modelului:** un set de 30 de întrebări scrise de noi, cu răspunsul corect; se alege modelul cu cele mai multe potriviri.
- **Gata când:** „what's a good crop for the field by the river” duce la fluxul de rotație.

### G. „Correct us” și constrângerile fermierului — Should

- Fermierul poate corecta cultura fiecărui an și poate spune dacă irigă. Totul primește eticheta „you told me”.
- Trei întrebări puse o singură dată în conversație: irigare, utilaje, ce culturi poate vinde. Culturile imposibile ies din listă.
- Cere stocare pe server (un fișier JSON per utilizator ajunge pentru demo).
- **Solul:** dacă SoilGrids are valori pentru parcelă, aplicația le folosește fără să întrebe nimic și le arată ca „Estimate for your area · 250 m”; fermierul le poate corecta. Dacă nu are (`sources.soil.status` e „pending”), asistentul spune „I have no soil data for this place” și pune o singură întrebare cu răspunsuri la o atingere: „Sandy / Loam / Clay / I don't know”. Răspunsul primește eticheta „you told me”. Pentru parcelele noastre există valori, deci întrebarea nu apare.

### H. Scenarii — Should

- Butoane sub recomandare: „Drier year”, „Hotter year”. Serverul scalează ploaia cu 0,8 sau mută temperatura cu +2 °C și reface rejucarea.

### I. Harta zonelor din parcelă — Should

- Un strat nou în harta Leaflet din My land, desenat din `zones.geojson` (Sentinel-2, 10 m): pătratele care au fost mai slabe în mai mulți ani. Serverul le dă printr-o adresă nouă, `GET /fields/{id}/zones`.
- Textul rămâne despre ce se vede, nu despre cauză: „This part was less green than the rest of the field in 4 of 8 years.” Eticheta: „Measured on your field · 10 m · ESA”.
- Depinde de C (descărcarea Sentinel-2). Stratul NASA GIBS cu cursor de dată iese din plan.

### J. Panta terenului — Could

- Din NASADEM, prin `field_pull.py` (vezi C): un rând la detaliile parcelei și, pe hartă, pătratele abrupte și locurile joase din `relief.geojson`.
- La 30 m, o parcelă îngustă are doar câteva pătrate (Lunca Jiului are 71 m lățime), deci la parcelele mici rămâne doar rândul cu panta medie.

### K. Pagina de limite și comparația de modele — Could

- Tabel mic: „media aceleiași săptămâni din anii trecuți” față de un model învățat, testate pe ani lăsați deoparte. Se sare dacă nu e timp.

### L. Recunoașterea vocii — Could

- O bibliotecă de recunoaștere vocală cere un build de dezvoltare, nu merge în Expo Go. De verificat care e compatibilă cu SDK 58. Varianta de rezervă există deja: microfonul tastaturii.

---

## 5. Planul pentru parcele de orice mărime

### 5.1 Principiul

Mărimea parcelei nu hotărăște dacă fermierul primește ajutor, ci doar pe ce cale. Vremea, apa din sol și regulile de rotație sunt identice pentru 5 ari și pentru 50 ha. Doar citirea din satelit a culturii depinde de mărime.

### 5.2 Ce poate vedea fiecare satelit

Un pătrat de imagine e „curat” doar dacă stă în întregime în parcelă. Ca să garantăm asta fără să știm cum cade grila peste parcelă, micșorăm conturul spre interior cu jumătate din diagonala pătratului și numărăm câte pătrate încap în ce rămâne.

| Sursă | Latura pătratului | Suprafața unui pătrat | Micșorare spre interior |
|---|---|---|---|
| HLS (NASA: Landsat 8/9 + Sentinel-2) | 30 m | 9 ari | 21 m |
| Sentinel-2 (ESA) | 10 m | 1 ar | 7 m |
| MODIS (NASA) | 250 m | 6,25 ha | 177 m |

Calculat pentru parcelele noastre:

| Parcelă | Suprafață | Dreptunghiul minim | Pătrate curate HLS 30 m | Sentinel-2 10 m | MODIS 250 m |
|---|---|---|---|---|---|
| Valea Mare | 11,15 ha | 263 × 470 m | 93 | 1018 | 0 |
| Dealul Viei | 6,25 ha | 216 × 302 m | 48 | 555 | 0 |
| Lunca Jiului | 2,14 ha | 71 × 319 m | 8 | 162 | 0 |
| Pădurea Veche | 11,18 ha | 288 × 468 m | 93 | 1021 | 0 |

Concluzii:

- MODIS nu poate citi nicio parcelă de-a noastră. Rămâne util doar pentru „împrejurimi”.
- HLS citește bine trei din patru. Lunca Jiului are 2 ha, dar e o fâșie de 71 m lățime și rămâne cu 8 pătrate curate.
- O parcelă de câțiva ari e mai mică decât un singur pătrat HLS. La 5 ari, nici Sentinel-2 nu are pătrate curate.

### 5.3 Cele patru niveluri

Nivelul se calculează automat din contur, la încărcarea parcelei. Pragurile sunt alegerea noastră și intră pe lista „de verificat”.

| Nivel | Condiție | Ce spune aplicația despre cultură | Eticheta din aplicație |
|---|---|---|---|
| **A. Citită din satelit** | Cel puțin 10 pătrate curate HLS | Cât de verde e parcela față de anii cu aceeași cultură | „Measured on your field · 30 m” |
| **B. Citită cu detaliu fin** | Sub 10 la HLS, dar cel puțin 10 la Sentinel-2 | La fel, din Sentinel-2 | „Measured on your field · 10 m · ESA” |
| **C. Împrejurimi** | Sub pragurile de mai sus | Cât de verde e zona din jur, plus ce spune fermierul | „Around your plot, not your plot” |
| **D. Fără contur** | Fermierul a pus doar un punct | Vremea din zonă, plus ce spune fermierul | „Estimate for your area” |

Ce primește **fiecare** nivel, fără deosebire: recomandarea de rotație, vremea, calendarul sezonului (fără rândul „verde” la C și D), scenariile.

Aplicat pe parcelele noastre: Valea Mare, Dealul Viei și Pădurea Veche sunt A. Lunca Jiului este B (Sentinel-2 e acum în plan).

### 5.4 Nivelul A: cum se calculează „cât de verde”

Funcția `pull_hls` din `backend/field_pull.py`, rulată o dată per parcelă, cu rezultatul păstrat pe disc.

1. **Colecții** (ID-urile exacte de verificat în catalogul Earth Engine): `NASA/HLS/HLSL30/v002` și `NASA/HLS/HLSS30/v002`.
2. **Mascare de nori:** se păstrează doar pătratele fără nor, umbră de nor, nor vecin și zăpadă, după banda `Fmask`.
3. **Indicele de verde (NDVI):** (infraroșu apropiat − roșu) / (infraroșu apropiat + roșu). Benzile diferă între cele două produse (la L30 infraroșul e B5, la S30 e B8A; roșul e B4 la ambele; de verificat).
4. **Reducere pe parcelă:** media și numărul de pătrate valide, pe conturul micșorat cu 21 m.
5. **Filtru de calitate:** o dată se păstrează doar dacă cel puțin 70% din pătratele curate sunt valide.
6. **Serie în timp:** valoarea maximă pe fiecare săptămână, ca să scăpăm de norii rămași.
7. **Referința:** media acelorași intervale din anii în care parcela a avut **aceeași cultură**. Dacă nu există cel puțin doi astfel de ani, aplicația arată curba anului fără nicio comparație.
8. **Starea parcelei:**
   - „As green as usual”: abaterea medie pe ultimele trei intervale e sub 10%;
   - „Less green than usual”: cu peste 10% sub referință;
   - „No clear images lately”: mai puțin de două date valide în ultimele 48 de zile;
   - „Too few years to compare”: lipsește referința.

HLS există din 2013 pentru Landsat și din 2015 pentru Sentinel-2, deci referința are cel mult 11–13 ani.

**Zone în interiorul parcelei** („o parte e mai puțin verde”) se fac acum cu Sentinel-2 la 10 m, unde parcelele noastre au între 162 și 1021 de pătrate curate (vezi 4.C și 4.I). Cu HLS la 30 m nu ar fi ajuns: parcelele mari au doar 93.

### 5.5 Nivelul C: împrejurimi și ochiul fermierului

Două surse care înlocuiesc citirea directă:

1. **Împrejurimile.** NDVI MODIS (`MODIS/061/MOD13Q1`, 250 m, la 16 zile) pe pătratele care ating parcela, comparat cu referința 2001–2020. Aceeași serie e istoricul de 20 de ani pentru toate parcelele, la orice nivel. Propoziția e despre zonă: „Crops around your plot are less green than usual.” Nu spune nimic despre parcela însăși.
2. **Fermierul.** O întrebare cu trei răspunsuri, pusă când întreabă de parcelă: „How does the crop look next to last year? Better / Same / Worse”. Răspunsul se păstrează cu data și cu eticheta „you told me” și apare în răspunsurile următoare.

Textul de bază pentru nivelul C: „This plot is too small for satellite images. I use the weather for your area, what grows around you, and what you tell me.”

### 5.6 Parcele mici alăturate

Dacă un fermier are mai multe parcele mici lipite, cu aceeași cultură, le putem uni într-un singur contur și citi împreună. Condiții: se ating, au aceeași cultură în acel an, iar împreună trec pragul nivelului A. Eticheta spune limpede: „Read together with 2 neighbouring plots”. Opțional; nu intră în programul de mâine.

### 5.7 Schimbări pe server

| Ce | Unde | Detalii |
|---|---|---|
| Numărul de pătrate curate și nivelul | `store.py` | Cu `shapely` (deja instalat): contur micșorat, suprafață împărțită la suprafața pătratului |
| Câmpuri noi la `/fields` | `main.py` | `tier` (A/B/C/D), `cleanPixels`, `sizeLabel` („11.2 ha” sau „35 ares”) |
| Citirea NDVI | `field_pull.py` (scris) | Pașii din 5.4 și 5.5; serverul citește `data/baked/<id>/profile.json` |
| Starea parcelei | `main.py` | `health` și `healthLabel` din rezultatul NDVI, după nivel |
| Graficul per parcelă | `analysis.py` | Card „How green the crop is”, cu `scope` „field” sau „around” |
| Întrebarea pentru parcele mici | `engine.py` | Răspuns nou cu id `look`; răspunsul salvat în `backend/cache/answers.json` |
| „How do you know?” | `engine.py` | Text după nivel: numărul de pătrate curate la A, explicația „prea mică” la C |

### 5.8 Schimbări în aplicație

| Ce | Unde |
|---|---|
| Tip nou `tier` și eticheta de mărime primită de la server | `src/types.ts`, `land.tsx` |
| A treia etichetă de proveniență: „Around your plot” | `data.tsx` (componenta `ScopeTag`) |
| Culoare neutră pentru parcelele fără citire (există deja pentru `unknown`) | `FieldShape.tsx`, `LeafletMap.tsx` |
| Sugestia „Why did my corn do badly?” înlocuită cu una care merge la orice nivel | `src/i18n.tsx` |

### 5.9 Cum testăm

- Cele patru parcele reale dau: trei de nivel A și una de nivel C (sau B).
- Două parcele de probă adăugate doar pentru test: una de 5 ari și una de 30 de ari, lângă celelalte. Trebuie să iasă C, cu mărimea scrisă în ari.
- Pentru fiecare nivel, se parcurge în emulator: lista din My land, întrebarea despre parcelă, „How do you know?”, graficul din Data.
- O parcelă de nivel A fără ani cu aceeași cultură trebuie să spună „Too few years to compare”.

### 5.10 Cum arătăm asta la demo

1. Valea Mare (nivel A): citirea din satelit și recomandarea de rotație.
2. Lunca Jiului (nivel C): aplicația spune singură că parcela e prea îngustă și cere părerea fermierului.
3. O frază pentru juriu: „Aceeași recomandare de rotație pentru 5 ari și pentru 50 de hectare; doar proveniența datelor se schimbă, și e scrisă pe ecran.”

---

## 6. Programul de mâine

Sâmbătă, 14 noiembrie. Orele sunt orientative; ordinea contează.

| Când | Ce | Depinde de |
|---|---|---|
| Înainte de orice | Autentificarea Earth Engine (o comandă, făcută de proprietarul contului) | — |
| Primul lucru | `git init` în `TerraCycle` și primul commit | Decizia 1 din secțiunea 9 |
| Până la 10:00 | Datele de test aduse la zi (B), apoi pornit build-ul APK | Cont Expo |
| Până la 12:00 | APK instalat pe telefonul de demo: **primul termen** | Build-ul |
| În paralel cu build-ul | Nivelurile de parcelă pe server și în aplicație (5.7, 5.8, fără NDVI) | — |
| După-amiază | `field_pull.py` rulat pe toate sursele, apoi serverul citește `profile.json` | Autentificarea |
| După-amiază | Tabelul de culturi cu surse (cineva din echipă caută valorile) | — |
| Seara | Motorul cu rejucarea anilor (D) și punctele de încredere pe card | Tabelul de culturi |
| Seara, dacă rămâne timp | Calendarul sezonului (E) | D și C |

Duminică dimineață, până la 12:00: AI-ul local (F), repetiția demo-ului, înregistrarea video de rezervă.

Ce se taie primul dacă nu ajunge timpul, în ordine: GAEZ, K, J, L, I, H, G.

---

## 7. Riscuri pentru demo

| Risc | Ce facem |
|---|---|
| Telefonul nu ajunge la laptop (alt Wi-Fi, firewall) | Un al doilea APK cu date de test aduse la zi, instalat dinainte |
| Internetul pică | Serverul folosește copia din `backend/cache/`. NDVI-ul se calculează dinainte și se păstrează tot acolo |
| Earth Engine nu se autentifică sau e lent | Demo-ul merge pe vreme și rotație; parcelele spun „No satellite reading yet” |
| Modelul local greșește sau întârzie | Potrivirea pe cuvinte și butoanele merg fără el |
| Emulatorul e lent pe laptop | Demo-ul se face pe telefon; emulatorul e doar pentru lucru |
| Un agronom din juriu contestă o regulă | Fiecare valoare din tabel are sursă, iar aplicația spune „check this locally” |
| Fereastra emulatorului iese din ecran | `Alt+Space → Move`, apoi săgețile. Poziția e în `%USERPROFILE%\.android\avd\TerraPixel.avd\emulator-user.ini` |

---

## 8. Cum pornești totul

Trei terminale noi (PowerShell).

**Serverul:**
```
cd Desktop\TerraCycle\backend
$env:PYTHONIOENCODING='utf-8'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

**Emulatorul:**
```
& "$env:LOCALAPPDATA\Android\Sdk\emulator\emulator.exe" -avd TerraPixel -gpu swiftshader_indirect
```
După ce pornește:
```
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
& $adb reverse tcp:8081 tcp:8081
& $adb reverse tcp:8000 tcp:8000
```

**Aplicația:**
```
cd Desktop\TerraCycle\app
npx expo start --go --localhost
```
Apoi tasta `a` în terminalul Expo.

De știut:

- Descărcarea datelor (o singură dată): `.\.venv\Scripts\python.exe field_pull.py` din `backend/`. Fără Earth Engine: adaugă `--only power,soil`.
- Serverul nu se reîncarcă singur când schimbi codul Python; se oprește și se pornește din nou.
- Dacă `npm install` dă eroare de dependențe: `npm install --legacy-peer-deps`.
- Aplicația fără server: șterge valoarea lui `EXPO_PUBLIC_API_URL` din `app/.env` și repornește Expo.
- Verificarea de tipuri: `npx tsc --noEmit` din `app/`.

---

## 9. Decizii pe care le așteptăm de la echipă

1. **Git:** hotărât. `TerraCycle` e depozit separat, cu GitHub ca `origin`.
2. **Culturile reale:** ce s-a cultivat pe cele patru parcele în 2024, 2025 și 2026? Fără ele, rotația pleacă de la un istoric inventat și nivelul A nu are „ani cu aceeași cultură”.
3. **Numele parcelelor:** le păstrăm pe cele inventate sau le punem pe cele adevărate?
4. **Sentinel-2:** hotărât. Îl folosim pentru harta parcelei și pentru nivelul B, etichetat pe ecran ca satelit european; HLS rămâne citirea NASA a parcelei.
5. **Prioritatea „Income”:** nu avem date de prețuri. O păstrăm ca valoare introdusă de fermier, marcată „not from NASA”, sau o scoatem?
6. **Cine caută valorile pentru tabelul de culturi** și din ce surse?
7. **Telefonul de demo:** ce model este și pe ce Wi-Fi va fi la prezentare?
