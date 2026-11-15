# 🛒 Retail Data Analytics

<p align="center"><strong>PYTHON-DA-TEAM · RETAIL DATA ANALYTICS</strong></p>
<p align="center"><em>Umsatzanalyse · Datenqualität · Retouren · Vereinfachte Ergebnisrechnung</em></p>
<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white">
  <img alt="pandas" src="https://img.shields.io/badge/pandas-150458?style=flat-square&logo=pandas&logoColor=white">
  <img alt="NumPy" src="https://img.shields.io/badge/NumPy-013243?style=flat-square&logo=numpy&logoColor=white">
  <img alt="Matplotlib" src="https://img.shields.io/badge/Matplotlib-0F172A?style=flat-square">
  <img alt="SQLite" src="https://img.shields.io/badge/SQLite-003B57?style=flat-square">
  <img alt="Lernprojekt" src="https://img.shields.io/badge/Projekt-Lernmaterial-orange?style=flat-square">
</p>

Ein gemeinsames Lernprojekt zur Aufbereitung und Analyse von Einzelhandelsdaten für 2024 und 2025. Python-Auswertungen verbinden Datenbereinigung, Produkt- und Filialanalysen, Retouren und eine vereinfachte monatliche Ergebnisrechnung. Die Ergebnisse sind Tabellen und statische Diagramme, keine produktive BI-Anwendung.

> [!NOTE]
> **Aktueller Stand:** Im Repository stehen `main.py` mit integrierter Datenbereinigung und 22 Analyseaufgaben sowie die einzelnen Aufgabenskripte mit dem gemeinsamen Modul `cleaning.py` bereit. Die Implementierung enthält fachliche Vereinfachungen, die unten erläutert werden.

---

## 📋 Schnellnavigation

| Projekt kennenlernen | Mit dem Projekt arbeiten | Referenz |
| --- | --- | --- |
| [Überblick](#project-overview) | [Datenbereinigung](#data-cleaning-module) | [Kennzahlen](#metric-definitions-methodology) |
| [Technologien](#technology-stack) | [Ausführung](#running-the-project) | [Grenzen](#current-analytical-limitations) |
| [Dateien und Daten](#data-project-structure) | [Analyseaufgaben](#analytical-tasks) | [Zusammenarbeit](#team-workflow-submission) |

---

<a id="project-overview"></a>

## 📌 Projektüberblick

**Geschäftsfragen:** Welche Produkte und Kategorien tragen zum Umsatz bei? Wie unterscheiden sich Filialen? Welche Retourenmuster und Datenqualitätsprobleme sind erkennbar? Wie verändern sich Ergebnisse unter vereinfachten Kostenannahmen?

**Team:** Serhii (Team Lead), Dmytro, Svitlana, Yuliia und Oksana.

| Rolle | Nachvollziehbarer Umfang |
| --- | --- |
| Serhii | Team Lead im Lernprojekt; Koordination der Zusammenarbeit |
| Gemeinsame Projektleistung | Datenaufbereitung, 22 Analyseaufgaben, Ergebnistabellen und Visualisierungen |
| Zuordnung einzelner Module | Im Repository liegt keine vollständige, verifizierte Zuordnung aller Skripte zu einzelnen Mitgliedern vor |

Die Teamleitung ist eine organisatorische Rolle im Ausbildungsprojekt. Sie bedeutet weder kommerzielle Personalverantwortung noch alleinige Urheberschaft an allen Analysen. Konkrete Codebeiträge sind über die Git-Historie und ergänzende Aufgabenbelege zu beurteilen.


---

<a id="technology-stack"></a>

## 🛠 Technologien

| Aufgabe | Umsetzung |
| --- | --- |
| Datenaufbereitung und Auswertung | Python, pandas, NumPy |
| Datenvisualisierung | Matplotlib, Seaborn |
| Excel-Dateien einlesen und schreiben | pandas mit openpyxl |
| Zusammenarbeit | Git und GitHub |
| Ergänzende Datenbankbereinigung | Python-Modul sqlite3; nur bei vorhandener lokaler SQLite-Quelldatei |
| Quelldaten | CSV, TSV, JSON und Excel |

**Einordnung von SQL:** Die Hauptanalysen arbeiten mit pandas auf Tabellen-Dateien. `clean_database()` enthält ergänzende SQL-Korrekturen an einer Kopie einer optionalen Datenbank. Das Projekt ist kein umfassendes SQL-Reporting-Projekt.


---

<a id="data-project-structure"></a>

## 📁 Daten und Projektstruktur

```text
retail-data-analytics/
├── main.py                       # Bereinigung und 22 Analyseaufgaben
├── cleaning.py                   # Gemeinsames Modul der Einzelskripte
├── task_1_*.py / task_2_*.py       # Einzelne Aufgaben
├── company_data.xlsx             # Stammdaten in mehreren Tabellenblättern
├── *.csv                         # Transaktionen, Retouren und weitere Tabellen
├── support_tickets.tsv
├── api_logs.json
├── README.md                     # Aktuelle deutsche Dokumentation
└── README_UA.md                   # Frühere ukrainische Projektbeschreibung
```

`cleaned_data/` und `results/` entstehen lokal beim Ausführen. Die optionale `analytics_practice.db` gehört nicht zum veröffentlichten Dateibestand. Die analytischen Aufgaben benötigen diese Datenbank nicht.


| Quelldatei | Inhalt |
| --- | --- |
| company_data.xlsx | Kunden, Produkte, Filialen, Mitarbeitende und Bestände |
| transactions.csv | Transaktionen, Mengen, Rabatte, Beträge und Retourenkennzeichen |
| returns.csv | Retouren, Gründe, Erstattungen und Datumsangaben |
| marketing.csv | Kampagnen und Budgets |
| salaries.csv | Gehaltsbestandteile und Nettolohnzahlungen |
| customers.csv / employees.csv / stores.csv | Zusätzliche Stammdatentabellen |
| support_tickets.tsv / api_logs.json | Supportvorgänge und API-Protokolle |

Verknüpfungen erfolgen vor allem über `customer_id`, `product_id`, `store_id` und `employee_id`.

---

<a id="data-cleaning-module"></a>

## 🧹 Datenbereinigung

Die Bereinigung ist in [cleaning.py](cleaning.py) implementiert und zusätzlich in [main.py](main.py) integriert:

- Textwerte vereinheitlichen, Leerzeichen entfernen und definierte Fehlwertdarstellungen erkennen.
- Vollständig doppelte Zeilen entfernen sowie Zahlen, Datumswerte und boolesche Werte konvertieren.
- Ausgewählte IDs gegen Stammdateien prüfen und ungültige Werte als fehlend markieren.
- Unterstützte fehlerhafte Transaktionszeilen reparieren; nicht lesbare Zeilen im Parserbericht zählen.
- Transaktionsbeträge mit Menge, Produktpreis und Rabatt abgleichen. Für als Retoure markierte Zeilen wird ein negativer Betrag erwartet.
- Bereinigte Dateien und einen Bericht über Zeilen, Fehlwerte und Parserergebnisse erzeugen.

> [!IMPORTANT]
> Die Bereinigung ersetzt nicht alle fehlenden Werte und stellt keinen vollständigen Schema- oder Integritätsnachweis dar. Der Betragabgleich verwendet den Preis aus dem Produktstamm. Ohne historische Preise ist das keine unabhängige Prüfung des tatsächlich vereinbarten Verkaufspreises.

<details>
<summary>Cache und erneute Ausführung</summary>

Vorhandene bereinigte Dateien werden wiederverwendet. Die Existenzprüfung kontrolliert weder Änderungszeiten der Quelldaten noch die inhaltliche Gültigkeit des Caches. Bei geänderten Daten die vorhandene Ausgabe sichern, den Cache gezielt neu erzeugen und Ergebnisse erneut prüfen. Die optional bereinigte SQLite-Datei wird von der Cacheprüfung nicht erfasst.

</details>


---

<a id="running-the-project"></a>

## ▶️ Ausführung

### Installation

Python mit einer kompatiblen pandas-Version verwenden; das Projekt nutzt unter anderem `format="mixed"` und benötigt daher pandas ab Version 2.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install "pandas>=2" numpy matplotlib seaborn openpyxl
```

### Gesamtablauf

```powershell
.\.venv\Scripts\python.exe main.py
```

### Einzelne Aufgabe

```powershell
.\.venv\Scripts\python.exe cleaning.py
.\.venv\Scripts\python.exe task_1_07_abc_analysis_of_products.py
.\.venv\Scripts\python.exe "task_2_10_P&L_Financial_Modeling.py"
```

Quellen müssen im Projektordner liegen. Der Ablauf erzeugt CSV-Tabellen und PNG-Grafiken in aufgabenspezifischen Unterordnern von `results/`. Vorhandene gleichnamige Ausgaben können überschrieben werden.

**Prüfstand dieser Dokumentation:** README, Dateistruktur und Implementierungen wurden abgeglichen. Diese Dokumentationsaktualisierung ist kein erneuter vollständiger Lauf aller Aufgaben und keine Bestätigung, dass alle oben genannten fachlichen Grenzen behoben wurden.


---

<a id="analytical-tasks"></a>

## 📊 Analyseaufgaben

Die Funktionen sind in `main.py` integriert; die gleichnamigen Einzelskripte stehen zusätzlich im Stammverzeichnis.

| Aufgabe | Inhalt | Methode / Ausgabe |
| --- | --- | --- |
| 1_01 | Umsatzstärkste Produkte | Gruppierung und Rangliste |
| 1_02 | Kategorieumsatz nach Monat | Pivot-Tabelle; Monatsnummer ohne Jahr |
| 1_03 | Durchschnittlicher Belegwert je Filiale | Umsatz je eindeutiger Transaktions-ID |
| 1_04 | Kategorievergleich 2024/2025 | Gruppierung und Balkendiagramm |
| 1_05 | Zusammenhänge zwischen Preis, Marge, Menge und Betrag | Korrelationsmatrix und Heatmap |
| 1_06 | Verteilung von Verkaufswerten | Boxplot, Violinplot und Dichtekurve |
| 1_07 | ABC-Klassifikation | Kumulierte Umsatzanteile; Grenzen bei 70 % und 90 % |
| 1_08 | Gemeinsam auftretende Kategorien | Paare je Kunde und Kalenderwoche; keine gesicherte Warenkorbzuordnung |
| 1_09 | Rabatte und Absatz | Beobachtete Mittelwerte mit und ohne Rabatt |
| 1_10 | Kundenbindung | Monatskohorten und Wiederkäufe in der Ausgangskategorie |
| 1_11 | Historischer Kundenwert-Score | Vereinfachte CLV-Formel und Rangquartile |
| 2_01 | Monatlicher Gewinnansatz | Verkäufe ohne Retouren, Wareneinsatz und 5-%-Kostenpauschale |
| 2_02 | Umsatzkonzentration | Pareto-Auswertung bis zur 80-%-Grenze |
| 2_03 | Datenqualität | Vier Teilkennzahlen für fünf rohe CSV-Dateien |
| 2_04 | Monatlicher Umsatz und Kosten | Neu berechnete Beträge und gestapeltes Diagramm |
| 2_05 | Produktumsatzkonzentration | Pareto-Kurve mit kumuliertem Anteil |
| 2_06 | Mehrteilige Übersicht | Umsatz, Filialformate, Retouren und Transaktionen |
| 2_07 | Tagesentwicklung | Gleitmittel über 7/30 Beobachtungen und einfache Auffälligkeitsregel |
| 2_08 | Retouren | Kategorien, Gründe, Erstattungen, Zahlungsarten und Rückgabedauer |
| 2_09 | Filialvergleich | Umsatz pro Quadratmeter und aktivem Mitarbeitenden |
| 2_10 | Vereinfachte monatliche P&L | Umsatz, Wareneinsatz, Marketing, Personal und Kostenpauschale |
| 2_11 | Monatliche KPI-Berichte | Statische PNG-Berichte für drei ausgewählte Monate |

### Praktischer Nutzen

Die Auswertungen machen Umsatzschwerpunkte, Datenprobleme und Unterschiede zwischen Produkten beziehungsweise Filialen sichtbar. Sie dienen als Übung für Reporting und betriebswirtschaftliche Datenanalyse. Eine tatsächlich erzielte Umsatzsteigerung, Kosteneinsparung oder Prozessverbesserung wird nicht nachgewiesen.


---

<a id="metric-definitions-methodology"></a>

## 📐 Kennzahlen und Methodik

### Vereinfachte Ergebnisrechnung

In `task_2_10_pnl_financial_modeling()` gilt:

```text
Umsatz = Summe total_amount
Wareneinsatz = Summe quantity × cost_price
Bruttogewinn = Umsatz − Wareneinsatz
Operatives Ergebnis = Bruttogewinn − Marketing − Nettolohnzahlungen − 5 % des Umsatzes
```

Marketingbudgets werden gleichmäßig auf die berührten Kampagnenmonate verteilt. Personalkosten basieren auf `net_pay`, nicht auf vollständigen Arbeitgeberkosten. Die 5-%-Pauschale ist eine Aufgabenannahme.

> [!WARNING]
> Die bestehende Ausgabespalte `Net Margin %` verwendet das operative Ergebnis und ist daher keine Nettogewinnmarge nach Zinsen und Steuern. Retouren vermindern den Umsatz, während die zugehörigen Produktkosten in dieser Berechnung nicht rückgebucht werden. Das Modell ist keine fachlich abschließend geprüfte Gewinn-und-Verlust-Rechnung.

### Datenqualität

[task_2_03_data_quality_score.py](task_2_03_data_quality_score.py) bewertet `customers.csv`, `employees.csv`, `marketing.csv`, `stores.csv` und `returns.csv` anhand von Vollständigkeit, vollständigen Zeilenduplikaten und ausgewählten Gültigkeits- und Konsistenzregeln. Der Gesamtscore ist das ungewichtete Mittel dieser vier Werte. Er beschreibt die implementierten Regeln, nicht die vollständige Qualität aller Daten.


---

<a id="current-analytical-limitations"></a>

## ⚠️ Aktuelle fachliche Grenzen

<details>
<summary>Weitere methodische Einschränkungen</summary>

- **Unterschiedliche Umsatz- und Gewinnbegriffe:** Aufgaben behandeln Retouren nicht einheitlich. Aufgabe 2_01 zieht eine Kostenpauschale ab; das KPI-Dashboard 2_11 zeigt Bruttogewinn vor Marketing und Personal. Zahlen sind daher nicht ungeprüft vergleichbar.
- **Rabatte und Mengen:** Aufgaben 2_04/2_05 berechnen Umsatz erneut, machen Mengen positiv und interpretieren Rabattwerte über 1 als Prozentangaben. Dadurch entstehen Abweichungen zur zentralen Bereinigung; insbesondere sind Werte von 1 oder darunter mehrdeutig. Fehlende Mengen werden dort teilweise durch 1 ersetzt.
- **Zeitliche Gruppierung:** Aufgabe 1_02 gruppiert nach Monatsnummer ohne Jahr. Aufgabe 1_08 verwendet Kunde und ISO-Wochennummer ohne ISO-Jahr. Unterschiedliche Jahre können zusammenfallen.
- **Kategoriepaare:** Gemeinsam beobachtete Kategorien innerhalb einer Kundenwoche sind nicht automatisch Bestandteile derselben Bestellung.
- **CLV:** Der historische Score multipliziert einen bereits frequenzabhängigen Umsatzwert nochmals mit der Kaufhäufigkeit. Er ist keine validierte Prognose zukünftiger Gewinne. Quartile sind keine Clusteranalyse.
- **Zusammenhang statt Ursache:** Rabattvergleiche und Korrelationen belegen keine kausale Wirkung.
- **Auffällige Tage:** Aufgabe 2_07 prüft den absoluten Tagesunterschied gegen zwei Standardabweichungen. Der Mittelwert des Unterschieds wird nicht abgezogen. Fehlende Kalendertage werden nicht ergänzt.
- **Retouren:** Kategoriequoten verwenden Datensätze aus der Retourendatei, Zahlungsartenquoten dagegen das Kennzeichen in den Transaktionen. Die Quellen müssen vor einer gemeinsamen Interpretation abgeglichen werden.
- **KPI-Dashboard:** `generate_dashboard()` erstellt statische PNG-Dateien mit sechs Karten und zwei Diagrammen. `Avg Order Value` wird dort durch die Anzahl der Verkaufszeilen geteilt; ohne belegte Gleichheit von Zeile und Bestellung ist dies kein eindeutiger Bestellwert.
- **Vollständigkeit:** Fehlende Werte können in Aggregationen ausgeschlossen oder in einzelnen Aufgaben ersetzt werden. Das muss bei der Interpretation berücksichtigt werden.

</details>


---

<a id="team-workflow-submission"></a>

## 👥 Zusammenarbeit und Abgabe

**Python-DA-Team:** Serhii (Team Lead), Dmytro, Svitlana, Yuliia und Oksana.

Der dokumentierte Arbeitsablauf des Lernprojekts:

```text
[ Persönliche Branches ] → [ Integration: Serhii ] → [ Review / Prüfung ] → [ Freigabe ] → [ main ]
```

Diese Prozessbeschreibung ist kein Nachweis, dass jeder Prüfschritt für jede Datei vollständig durchgeführt wurde. Eine vollständige individuelle Zuordnung der Analyseaufgaben ist nicht dokumentiert.

Der veröffentlichte `main.py` enthält bereits die Datenbereinigung und die Aufrufe aller 22 Aufgaben. Ein vollständiger Abschlussnachweis mit fachlich korrigierten Berechnungen und einer zugehörigen Präsentation wird durch dieses README nicht behauptet.

## 🔎 Sinnvolle nächste Schritte

- Umsatz, Retouren, Beleganzahl und Gewinnbegriffe über die Aufgaben vereinheitlichen.
- Die Ergebnisrechnung und Rabattinterpretation fachlich korrigieren und anhand geeigneter Fälle prüfen.
- Periodengruppierungen um das Jahr ergänzen und Cacheverwendung nachvollziehbar machen.
- Persönliche Beiträge anhand konkreter Aufgaben und Änderungen dokumentieren.
- Nach fachlichen Korrekturen einen vollständigen Lauf mit reproduzierbaren Abhängigkeiten und geprüften Ergebnisdateien dokumentieren.

Diese Punkte sind Weiterentwicklung, keine bereits umgesetzten Funktionen. Die frühere ukrainische Dokumentation ist ein historischer Stand; maßgeblich für den aktuellen Umfang sind dieses README und der Code.


### Lizenz

Siehe [LICENSE](LICENSE).
