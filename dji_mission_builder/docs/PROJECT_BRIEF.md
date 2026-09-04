# Project Brief — DJI Mapping Mission Builder

## 1. Doel

Bouw een desktop/web-based tool waarmee ik voor een **DJI Mini 5 Pro + DJI RC 2** waypoint- en mappingmissies kan maken, aanpassen, controleren en exporteren als een DJI-compatibele `.KMZ`.

De tool moet zowel handmatige configuratie als AI-ondersteunde configuratie mogelijk maken.

Het belangrijkste principe:

> **De AI bepaalt wat de gebruiker bedoelt; de software berekent en genereert de daadwerkelijke vliegmissie deterministisch.**

De tool mag dus nooit "op goed geluk" XML/KMZ aanpassen.

---

## 2. Kernfunctionaliteit

### A. Bestaande KMZ importeren

Gebruiker kan een bestaande DJI `.KMZ` importeren.

De software:

1. opent het KMZ-archief;
2. detecteert de WPML/KML-bestanden;
3. leest de bestaande missie;
4. toont de waypoints en route op een kaart;
5. toont alle relevante missieparameters;
6. maakt duidelijk welke parameters gewijzigd kunnen worden;
7. valideert de originele missie voordat wijzigingen worden toegepast.

De originele file moet altijd onaangeroerd blijven.

---

## 3. Nieuwe mappingmissie maken

Gebruiker kan een gebied op een kaart tekenen of een bestaand gebied importeren.

Instellingen:

### Vlucht

- Drone: DJI Mini 5 Pro
- Hoogte AGL
- Vliegsnelheid
- Vliegrichting
- Startpunt
- Eindpunt
- Turn mode
- Waypoint heading
- Gimbal pitch
- Hover/dwell time

### Mapping

- Front overlap %
- Side overlap %
- Camera orientation
- Foto/video
- Foto-interval
- Ground sampling / gewenste resolutie indien mogelijk
- Aantal vlieglijnen
- Afstand tussen vlieglijnen
- Afstand tussen foto's

De software berekent vervolgens automatisch:

`gebied → flight grid → waypoints → camera actions → WPML → KMZ`

---

## 4. AI-assistent

Een chatveld waarin de gebruiker opdrachten in normale taal kan geven.

Voorbeeld:

> Map boerderij Jos op 100 meter. Gebruik 80% front overlap en 70% side overlap. Vlieg de lange zijde eerst en maak foto's tijdens de vlucht.

De AI vertaalt dit naar gestructureerde parameters.

Bijvoorbeeld:

```json
{
  "mission_type": "mapping_2d",
  "altitude_m": 100,
  "front_overlap": 0.80,
  "side_overlap": 0.70,
  "speed_ms": 5,
  "gimbal_pitch": -90,
  "camera_action": "photo",
  "flight_direction": "long_axis"
}
```

Daarna geeft de software de gebruiker een preview.

**AI mag niet rechtstreeks de KMZ/XML genereren.**

Een aparte mission-engine doet dat.

---

# 5. Missietypes

Gebruik een gestandaardiseerde lijst.

Bijvoorbeeld:

- `WP2D` — 2D mapping
- `WP3D` — 3D mapping
- `WPINS` — inspectie
- `WPVID` — video
- `WPGEN` — algemene waypoint mission

De exacte lijst kan later worden uitgebreid.

Voor mapping zou ik **WP2D** en **WP3D** expliciet onderscheiden.

---

# 6. Bestandsnaamstandaard

De bestandsnaam moet automatisch worden gegenereerd.

Formaat:

```text
YYYYMMDD_TYPE_NAME.kmz
```

Voorbeeld:

```text
20260902_WP2D_BoerderijJos.kmz
```

Voor 3D:

```text
20260902_WP3D_BoerderijJos.kmz
```

Voor inspectie:

```text
20260902_WPINS_BoerderijJos.kmz
```

### Naamveld

De gebruiker krijgt één vrij tekstveld:

```text
Naam / locatie:
[ Boerderij Jos ]
```

De software maakt daar een veilige bestandsnaam van.

Bijvoorbeeld:

`Boerderij Jos` → `BoerderijJos`

Speciale tekens verwijderen.

Geen spaties.

Geen `/ \ : * ? " < > |`.

Optioneel maximaal bijvoorbeeld 40 tekens.

---

# 7. Versiebeheer

Omdat dezelfde locatie meerdere keren gevlogen kan worden, moet een optionele versie worden ondersteund.

Bijvoorbeeld:

```text
20260902_WP2D_BoerderijJos_v01.kmz
20260902_WP2D_BoerderijJos_v02.kmz
20260902_WP2D_BoerderijJos_v03.kmz
```

De software kan automatisch het volgende beschikbare versienummer kiezen.

Daarnaast moet de originele geïmporteerde KMZ nooit worden overschreven.

---

# 8. Missie-ID

Elke gegenereerde missie krijgt intern een unieke ID.

Bijvoorbeeld:

```text
mission_id:
20260902-WP2D-BoerderijJos-01
```

Deze ID hoeft niet noodzakelijk identiek te zijn aan de DJI-bestandsnaam.

Bewaar daarnaast metadata:

```text
Created
Modified
Mission type
Location/name
Drone
Altitude
Overlap
Speed
Version
Source KMZ
```

---

# 9. Kaartinterface

De hoofdinterface bestaat uit:

### Links

Missie-instellingen.

### Midden

Interactieve kaart.

Toon:

- polygon van het gebied;
- waypoints;
- flight lines;
- vliegrichting;
- startpunt;
- eindpunt;
- camera orientation;
- geschatte route;
- geschatte afstand;
- geschatte vliegtijd;
- aantal foto's.

### Rechts

Missie-informatie:

```text
Mission
Boerderij Jos

Type
WP2D

Altitude
100 m

Front overlap
80%

Side overlap
70%

Distance
4.8 km

Photos
184

Estimated flight time
17:20
```

---

# 10. Preview vóór export

Nooit direct een KMZ exporteren zonder validatie.

Workflow:

```text
CREATE
   ↓
CALCULATE
   ↓
PREVIEW
   ↓
VALIDATE
   ↓
EXPORT KMZ
```

Bij fouten:

```text
ERROR
Altitude missing

WARNING
Mission contains parameters unsupported
by the selected aircraft.
```

---

# 11. DJI-compatibiliteit

De software moet specifiek worden gebouwd tegen het **DJI WPML/KMZ-formaat** en niet tegen een zelfbedacht formaat.

Belangrijk:

- bestaande DJI-KMZ kunnen importeren;
- WPML XML correct behouden;
- noodzakelijke DJI metadata behouden;
- alleen ondersteunde parameters wijzigen;
- XML valideren;
- KMZ correct opnieuw zippen;
- compatibiliteit met de Mini 5 Pro controleren.

De software moet onderscheid maken tussen:

**Editable**

en

**Do not modify**

zodat DJI-specifieke metadata niet per ongeluk wordt verwijderd.

---

# 12. Veiligheidslaag

Voor export controleert de software minimaal:

- hoogte;
- aantal waypoints;
- geldige GPS-coördinaten;
- routecontinuïteit;
- ontbrekende parameters;
- ongeldige waarden;
- camera-acties;
- drone/modelcompatibiliteit;
- WPML-structuur;
- XML-validiteit.

Daarnaast:

> **De software start nooit de drone.**

Hij maakt uitsluitend een missiebestand.

De gebruiker importeert/activeert de missie zelf in DJI Fly.

---

# 13. Import → aanpassen → export

Een belangrijke use-case:

```text
DJI KMZ
   ↓
IMPORT
   ↓
analyse
   ↓
kaart + instellingen
   ↓
AI / handmatige wijziging
   ↓
recalculate
   ↓
validate
   ↓
EXPORT
   ↓
20260902_WP2D_BoerderijJos_v02.kmz
```

Dit moet net zo goed werken als een nieuwe missie.

---

# 14. "Quick Mission"

Voor dagelijks gebruik een eenvoudige modus.

Gebruiker vult alleen in:

```text
Naam:
[Boerderij Jos]

Type:
[2D Mapping]

Hoogte:
[100] m

Front overlap:
[80] %

Side overlap:
[70] %

Snelheid:
[5] m/s
```

Daarna:

**GENERATE MISSION**

---

# 15. Expert Mode

Voor gevorderde gebruikers alle DJI/WPML-gerelateerde instellingen beschikbaar maken.

De UI moet hierbij duidelijk aangeven:

- standaard;
- gewijzigd;
- DJI-specifiek;
- experimenteel;
- niet aanbevolen.

---

# 16. AI + deterministische engine

Architectuur:

```text
                USER
                  │
                  ▼
             AI ASSISTANT
                  │
                  ▼
          Mission Parameters
                  │
                  ▼
        ┌───────────────────┐
        │   MISSION ENGINE  │
        │                   │
        │ geometry          │
        │ overlap           │
        │ flight lines      │
        │ waypoints         │
        │ camera actions    │
        └─────────┬─────────┘
                  │
                  ▼
             WPML BUILDER
                  │
                  ▼
            VALIDATOR
                  │
                  ▼
              KMZ EXPORT
```

Dit voorkomt dat een taalmodel zelfstandig kritieke vliegparameters of XML-structuren gaat verzinnen.

---

# 17. Eerste MVP

De eerste versie hoeft nog niet alles te kunnen.

### MVP v0.1

1. KMZ import
2. KMZ uitpakken
3. WPML lezen
4. Waypoints tonen
5. Route tonen op kaart
6. Hoogte aanpassen
7. Snelheid aanpassen
8. Gimbal aanpassen
9. Foto-acties aanpassen
10. Validatie
11. KMZ opnieuw exporteren
12. Gestandaardiseerde bestandsnaam

Bestandsnaam:

```text
YYYYMMDD_TYPE_NAME_v01.kmz
```

### v0.2

- gebied tekenen;
- automatische mapping-grid;
- front overlap;
- side overlap;
- automatische foto-spacing;
- vliegrichting;
- startpunt;
- route-optimalisatie.

### v0.3

- AI-assistent;
- natuurlijke taal;
- missie-analyse;
- automatische parameterkeuze;
- foutmeldingen in gewone taal.

---

# 18. Belangrijk technisch uitgangspunt

Begin niet met het genereren van KMZ.

Begin met:

**één echte KMZ van de DJI RC 2 + Mini 5 Pro analyseren.**

Daarmee bepalen we exact:

- welke bestanden erin zitten;
- welke WPML-versie wordt gebruikt;
- welke tags DJI Fly daadwerkelijk schrijft;
- welke parameters de Mini 5 Pro gebruikt;
- welke waarden veranderen wanneer je één instelling wijzigt.

Daarna bouwen we de parser en generator rondom die echte structuur.

---

# 19. Gewenste eindervaring

Uiteindelijk moet dit mogelijk zijn:

> "Maak een 2D mapping-missie voor Boerderij Jos. 100 meter hoog, 80% front overlap, 70% side overlap, 5 meter per seconde. Vlieg noord-zuid."

De software toont de route.

Gebruiker controleert de preview.

Daarna:

**EXPORT**

→

```text
20260902_WP2D_BoerderijJos_v01.kmz
```

Klaar voor gebruik met de DJI-workflow.