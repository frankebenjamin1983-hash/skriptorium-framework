# PyCompendium – Style-Guide

> Status: **Entwurf** (von Claude in der Nacht verfasst, vom User noch
> nicht abgenommen). Wird in Stufe 2 jedem Autor- und Lektorats-Agenten
> als System-Prompt-Bestandteil mitgegeben.

## 0. Wer das Buch ist – in einem Satz

PyCompendium ist ein deutsches Python-Lehrbuch vom Anfänger zum Profi,
sachlich-didaktisch geschrieben, mit der trockenen Klarheit eines
Ostwestfalen. Keine Cheerleader-Sätze, keine künstliche Begeisterung,
aber auch keine Aktendeutsch-Bürokratie.

## 1. Tonalität

### Grundregel

Sachlich. Knapp. Wo sich ein Witz natürlich ergibt, wird er nicht
unterdrückt — aber er wird auch nicht erzwungen. Lieber ein gut
erklärter Begriff als ein bemühter Vergleich.

### Anrede

**Du**, nicht Sie. Das Buch redet mit dem Leser, nicht über ihn. „Du
schreibst", „du siehst", „dir fällt auf".

### Erlaubt

- Trockener Hinweis statt Warnschilder: „Diese Funktion wirft eine
  Exception, sobald du ihr `None` gibst. Das ist Absicht."
- Zynisch, wenn berechtigt: „Python erlaubt das, ja. Das heißt nicht,
  dass du es tun solltest."
- Selbstreferentiell, sparsam: „Wer dieses Buch chronologisch liest,
  weiß das schon aus Kapitel 4."

### Verboten

- „Lass uns gemeinsam erforschen, wie..." → künstliche Reise-Metaphern
- „Spannend, oder?" → keine Begeisterungs-Appelle
- „Ganz einfach!" → bevormundend; wenn es einfach wäre, müsste man es
  nicht sagen
- Ausrufezeichen am Satzende, außer in Code-Output
- Emojis im Fließtext (in Code-Kommentaren akzeptiert)

### Beispiele Vorher / Nachher

**Vorher:**
> Großartig! Jetzt schauen wir uns gemeinsam an, wie Listen funktionieren.
> Listen sind eine wirklich praktische Datenstruktur in Python!

**Nachher:**
> Listen halten geordnete Sammlungen veränderbarer Werte. Sie sind die
> häufigste Datenstruktur in Python, weil sie für 80 % der Fälle das
> Richtige tun.

---

**Vorher:**
> Achtung! Sei vorsichtig mit veränderbaren Default-Argumenten!

**Nachher:**
> Default-Argumente werden einmal ausgewertet, beim Funktions-Aufruf,
> nicht jedes Mal. Wer `def f(x=[])` schreibt, teilt die Liste zwischen
> allen Aufrufen. Das ist ein klassischer Anfänger-Bug, der erfahrene
> Entwickler genauso erwischt.

## 2. Aufbau eines Kapitels

Jedes Kapitel folgt derselben Form, weil sich das Buch sonst wie eine
Sammlung loser Vorträge liest. Vier feste Bausteine, in dieser Reihenfolge:

1. **Lernziele** (3–5 Stichpunkte) — was kann der Leser danach
2. **Einstieg** (1 Absatz) — wo steht das Thema im Python-Ökosystem,
   warum behandeln wir es jetzt
3. **Hauptteil** — frei strukturiert, aber mit `## Konzept` /
   `### Beispiel` / `### Stolperfalle`-Mustern
4. **Zum Mitnehmen** (Bullet-Liste) — die zwei oder drei Sätze, die
   in einem halben Jahr noch hängenbleiben sollen

Übungen kommen als eigene Datei daneben, nicht im Kapitel-Volltext.

## 3. Code-Konventionen

### Type Hints

**Ja** — überall in selbstgeschriebenen Beispielen ab Kapitel 5
(„Funktionen, fortgeschritten"). Davor weglassen, damit der Leser
nicht von Syntax erschlagen wird, die er noch nicht eingeordnet hat.

```python
# Vor Kapitel 5
def greet(name):
    return f"Hallo, {name}"

# Ab Kapitel 5
def greet(name: str) -> str:
    return f"Hallo, {name}"
```

### Strings

**f-strings only.** Keine `.format()`, kein `%s`, kein `+`-Konkatenieren
für Substitution. Punkt.

```python
# nein
"Hallo, " + name + "!"

# auch nein
"Hallo, %s!" % name

# nein
"Hallo, {}!".format(name)

# ja
f"Hallo, {name}!"
```

### Klassen

Im OOP-Kapitel ohne `@dataclass` erklären, damit `__init__`, `__repr__`
und Co. sichtbar werden. Ab dem zweiten OOP-Beispiel: `@dataclass`
wird der Default, alles andere wird Ausnahme mit Begründung.

### Moderne Features (Python 3.10+)

| Feature | Einsatz |
|---|---|
| f-strings | überall |
| Type Hints (PEP 604: `str | None`) | ab Kap. 5 |
| `match-case` | im Vertiefungs-Kapitel, nicht als if/elif-Ersatz |
| Walrus `:=` | sparsam, nur wenn er Code klarer macht |
| Generics ohne `typing.List` (`list[int]`) | überall |

### Code-Beispiel-Länge

Maximal 15 Zeilen pro Block. Wer mehr braucht, hat das Konzept nicht
sauber zerlegt. Längere Beispiele werden in „Schritt 1", „Schritt 2"
unterteilt.

### Imports in Beispielen

Imports stehen immer im Block, auch wenn es das Beispiel länger macht.
Niemand soll raten müssen, woher `Path` kommt.

### Output

Erwarteter Output kommt als Kommentar unter den Code-Block, mit `# →`
markiert:

```python
print(f"{2 ** 10:,}")
# → 1,024
```

## 4. Vokabular

Wir entscheiden ein für allemal:

| Begriff | Verwendung | Nicht |
|---|---|---|
| Funktion | global, definiert mit `def` | Methode |
| Methode | nur, wenn an Klasse gebunden | Funktion |
| Parameter | in der Definition (`def f(x):`) | Argument |
| Argument | beim Aufruf (`f(3)`) | Parameter |
| Liste | `list` | Array |
| Wörterbuch / Dict | `dict` | Hashmap |
| Tupel | `tuple` | n-Tupel |
| Iterable | alles mit `__iter__` | Iterator |
| Iterator | das, was `next()` weitergibt | Generator |
| Generator | spezielle Iterator-Form mit `yield` | Iterator |

Englische Begriffe in Code-Beispielen ja, im Fließtext deutsche
Übersetzung, englischer Begriff in Klammern beim ersten Vorkommen:

> Funktionen sind Bürger erster Klasse (*first-class citizens*) in Python.

## 5. Quellenbelege

Jede inhaltliche Aussage, die nicht trivial ist, bekommt eine Fußnote
auf die Quelle:

```markdown
Dataclasses ersetzen oft das manuelle Schreiben von `__init__`. ¹

---
¹ cs50p Lecture 8, OOP Masterclass §4.2
```

Der Faktenprüfer-Agent kann diese Fußnoten gegen die Original-Karten
abgleichen. Aussagen ohne Beleg gelten als unbelegt — wenn sie trivial
sind, ist das ok, sonst markiert der Faktenprüfer sie.

## 6. Diagramme und Abbildungen

Vorerst keine. Wenn ein Konzept ein Bild braucht (z. B. Speicherlayout
einer Liste), wird das mit ASCII gemacht:

```
list = [1, 2, 3]
       ┌───┬───┬───┐
       │ 1 │ 2 │ 3 │
       └───┴───┴───┘
       ↑           ↑
       list[0]     list[2]
```

Schwerere Grafik (Mermaid, Matplotlib-Output) erst, wenn MkDocs-Setup
das stabil rendert.

## 7. Was der Style-Guide NICHT regelt

- Welche Kapitel das Buch hat — das ist der Lektor
- Welche Beispiele in welchem Kapitel — das ist der Autor pro Kapitel
- Korrektheit der Fakten — das ist der Faktenprüfer

Style-Guide regelt nur, wie das Buch *klingt*, wenn man es liest.

---

*Stand:* Stufe 1 (Dummy-Pipeline). *Nächste Iteration:* nach dem
ersten echten Test-Kapitel in Stufe 2, mit Beispielen aus dem
tatsächlichen Output.
