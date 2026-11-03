# Sicherheitsaudit: Lemo-Opuscar (gehärtete Kopie)

Stand: 03.11.2026 · Quelle: `github.com/lemomo-ai/lemo-opuscar`, Commit `bebbbe1` (01.11.2026), Lizenz MIT

## Kurzfazit

In dem, was ich gelesen und gescannt habe, fand ich **keinen Schadcode** (kein `curl | sh`, keine Uploads, kein Zugriff auf `.ssh`/`.env`, keine Obfuskation, keine fremden Binärdateien, keine Symlinks). Es gab aber **Konstruktionsrisiken**, die diese Kopie entschärft:

| # | Fund | Schwere | Maßnahme |
|---|------|---------|----------|
| 1 | `setup.sh` machte bei jedem Start `fetch` + `reset --hard origin/main`: Code vom Autor lief ungeprüft nach | mittel | Clone/Update-Zweig entfernt. Die Bibliothek ist dieses Repo. |
| 2 | Headless-Chrome rendert vom Agenten geschriebene Seiten **ohne Netzwerkbeschränkung** (Nachladen von Fremdcode, Senden nach außen möglich) | mittel | `core/render/page.mjs`: nur `127.0.0.1`, `localhost`, `data:`, `blob:` erlaubt, alles andere geblockt und gemeldet. Getestet (Bild, Skript und `fetch` nach außen blockiert, Rendern läuft weiter). Abschaltbar mit `LEMO_ALLOW_NET=1` (nicht empfohlen). |
| 3 | Statischer Server prüfte Pfade, folgte aber **Symlinks** | niedrig | `core/render/serve.mjs`: `realpath`-Prüfung. Getestet: `../`, `%2e%2e`, Symlink und falscher `Host`-Header werden abgewiesen. |
| 4 | pip-Pakete ungepinnt, `npm install` mit Lifecycle-Skripten | niedrig | Alle drei Python-Stufen mit exakten Versionen und Hashes gesperrt (`--require-hashes --only-binary=:all:`), `npm ci --ignore-scripts`. Installation aller Stufen getestet. |
| 5 | Demo-Skripte: 44 laden Daten ohne Hash-Prüfung nach, 101 Shell-Buildskripte (teils mit `curl`), 1 liest `~/.codex`-Sessionlogs, 1 sendet Text mit eigenem Key an Bytedance (zusammen 147 Dateien) | niedrig (nur bei manueller Ausführung) | Entfernt, siehe `tools/REMOVED-FILES.txt`. |
| 6 | 5× `eval`/`exec`/`__import__` in Demo-Code | info | Einzeln geprüft: Arithmetik auf lokaler Datei, `exec` eines Nachbarskripts, Methodenname `.eval()`, `__import__('PIL…')`. Harmlos. |
| 7 | Mitgelieferte Bibliotheken (`opentype.min.js`, `topojson-client.min.cjs`) | info | Byte-identisch mit den offiziellen npm-Releases (opentype.js 1.3.4, topojson-client 3.1.0). |
| 8 | 7 Release-Pakete (Stimmmodell, Instrumente, HDRI) | info | Alle heruntergeladen: SHA256 stimmt mit `tools/assets.json`. Inhalt nur `.flac/.wav/.hdr/.sfz/.json/.txt/.md`, keine ausführbaren Dateien, Symlinks oder unsichere Pfade. ONNX-Modell: 49 Standard-Operatoren, keine Custom-Ops, keine externen Daten. Stimmdatei ohne Pickle-Objekte. |

## Methode

- **Python (336 Dateien):** AST-Scan auf `eval/exec/compile/__import__`, `os.system`, `subprocess`, `shell=True`, `urllib/requests/socket`, `pickle/marshal/ctypes`.
- **JS/MJS/HTML/Shell/Markdown:** Mustersuche auf Netzwerk, Prozessstart, Dateioperationen, Browser-Flags, Remote-Ladevorgänge, Secrets- und Fremdpfade.
- **Versteckte Tricks:** Bidi- und Zero-Width-Zeichen (Trojan Source), Null-Bytes, ungewöhnliche Dateinamen, Base64/`fromCharCode`/Packer, Zeilen > 4000 Zeichen, Prompt-Injection-Formulierungen in allen Textdateien. Einziger Treffer: ein Soft-Hyphen in der offiziellen `opentype.min.js`.
- **Vollständig gelesen:** `core/render/*` (alle), `core/tts/*`, `core/audio/sfx.py`, `core/lib.js`, `setup.sh`, `tools/fetch.sh`, `AGENTS.md`, `SKILL.md`.
- **Per AST bzw. Shader-Durchsicht:** `core/audio/sampler.py` (nur lokales Lesen von Samples/SFZ; Schreiben nur im Maintainer-Indexbau), `core/audio/pluck.py` (keine System- oder Dateizugriffe), `core/post/crt.js` und `core/three/post.js` (reine Shader/three-Postprocessing).
- **Nur per Mustersuche, nicht Zeile für Zeile:** die übrigen Markdown-Anleitungen (`DIRECTOR.md`, `TECHNIQUE.md`, `MY-STYLES.md`, 66× `STYLE.md`/`DEMO.md`) und der Demo-Referenzcode unter `styles/*/demo/`.

## Änderungen gegenüber Upstream

Geändert: `plugin/skills/lemo-opuscar/scripts/setup.sh`, `core/render/page.mjs`, `core/render/serve.mjs`, `plugin/skills/lemo-opuscar/SKILL.md` (1 Satz), `MAINTAINING.md` (1 Hinweis), `requirements*.txt` (gesperrt; Quellen in `requirements*.in`).
Neu: `tools/audit.py`, `tools/audited.sha256`, `tools/REMOVED-FILES.txt`, `README.md`, `SECURITY-AUDIT.md`.
Entfernt: siehe `tools/REMOVED-FILES.txt`.
Unverändert, aber relevant: `tools/fetch.sh` und `tools/assets.json` (Hash-Prüfung vor dem Entpacken, sicherer Tar-Filter).

## Restrisiken, die diese Kopie nicht beseitigt

1. **Der Agent selbst.** Claude Code führt Shell-Befehle und Dateizugriffe mit deinen Rechten aus. Gib keine pauschalen Berechtigungen, nutze einen Arbeitsordner ohne Zugangsdaten, und setze keine Secrets in die Umgebung. Die Anweisungstexte steuern den Agenten. Ich habe sie gescannt, aber nicht jede Zeile gelesen.
2. **Chromium-Download** (`playwright … install`) kommt vom Playwright-CDN über TLS und wird von diesem Repo nicht gehasht. Die Playwright-Version ist durch das Lockfile fest.
3. **Whisper-Modelle** (`asr_check.py`, nur Voice-Stufe) werden bei der ersten Nutzung ungepinnt von Hugging Face geladen.
4. **Edge-TTS** (`tts_zh.py`, optional) schickt den Sprechtext an Microsoft.
5. **Asset-Download** (`tools/fetch.sh`) zieht vom Release `assets` in `github.com/lemomo-ai/lemo-opuscar`. Per SHA256 gepinnt und am 03.11.2026 geprüft. Ändert Upstream das Release, bricht der Download mit Hash-Fehler ab. Wer unabhängig sein will: Pakete selbst spiegeln und `repo`/`tag` in `tools/assets.json` ändern.
6. **Registry-Vertrauen:** npm (`three`, `playwright-core`) und PyPI-Pakete sind per Integrity/Hash fixiert, aber nicht von mir auditiert.
7. **Material aus dem Web** (Dokumentar-Stile, eigene Quellen) kann Text enthalten, der den Agenten beeinflusst. Prüfe fremdes Material, bevor du es einspeist.
8. **Funktionsverlust:** Die 8 Dokumentar-Stile sowie Satellite Briefing und LiDAR Survey luden ihr Material über die entfernten Fetcher. Hier musst du eigenes Material liefern.
9. **Keine Garantie:** Statische Prüfung beweist nicht, dass etwas fehlt. Sie senkt das Risiko deutlich, ersetzt aber keinen Sandbox-Betrieb.

## Selbst nachprüfen

```sh
python3 tools/audit.py            # exit 0 nur wenn nichts vom geprüften Stand abweicht
python3 tools/audit.py --update   # erst NACH deiner Durchsicht einer Änderung
```

`audit.py` prüft: (1) alle Dateien gegen `tools/audited.sha256`, (2) riskante Muster nur in geprüften Dateien, (3) `package-lock.json` hat genau `playwright-core` und `three` mit Integrity, (4) jede Zeile in `requirements*.txt` ist gepinnt und gehasht, (5) alle Pakete in `assets.json` haben SHA256. Es nutzt nur die Python-Standardbibliothek und kein Netzwerk.

**Upstream-Updates übernehmen:** Änderungen nie blind kopieren. Neue Version klonen, `git diff` zwischen `bebbbe1` und dem neuen Stand lesen (besonders `setup.sh`, `core/`, `tools/`, `*.md`), dann gezielt übernehmen und `audit.py --update` ausführen.
