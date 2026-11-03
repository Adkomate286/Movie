# Lemo-Opuscar (gehärtete Kopie)

Filmstile aus Code für Claude Code: 66 Stile, ein Satz Auftrag, fertiger Film. Dies ist eine **geprüfte und gehärtete Kopie** von `lemomo-ai/lemo-opuscar` (Commit `bebbbe1`, 01.11.2026, MIT). Was geprüft und geändert wurde, steht in [`SECURITY-AUDIT.md`](SECURITY-AUDIT.md).

## In dein Repo bringen

```sh
git clone https://github.com/<DEIN-USER>/<DEIN-REPO>.git
cd <DEIN-REPO>
# Inhalt des Ordners lemo-opuscar-hardened hierher kopieren (inkl. versteckter Dateien wie .gitignore)
python3 tools/audit.py            # muss "AUDIT OK" ausgeben
git add -A
git commit -m "Lemo-Opuscar gehärtet (Upstream bebbbe1)"
git push
```

## Benutzen

Windows: in WSL2 (Ubuntu) arbeiten. Die Skripte sind `sh` und auf Mac/Linux gebaut.

Voraussetzungen: Node 20+, **ffmpeg 7+** (mit 6.x meldet `mux.sh` fälschlich beschädigtes Audio, Upstream-Bug #7), Python 3.11 bis 3.13 (oder `uv`), git, Claude Code.

```sh
git clone https://github.com/<DEIN-USER>/<DEIN-REPO>.git ~/lemo-opuscar   # kurzer Pfad: die Offline-Stimme verlangt ihn
cd ~/lemo-opuscar
python3 tools/audit.py                                                    # vor jedem Start
sh plugin/skills/lemo-opuscar/scripts/setup.sh deps                       # Grundstufe: npm ci, Chromium, Python (gesperrt)
sh plugin/skills/lemo-opuscar/scripts/setup.sh deps voice                 # optional: Stimme + Sprechprüfung (lädt ~350 MB, SHA256-geprüft)
claude                                                                    # im Ordner starten; AGENTS.md steuert alles
```

Dann zum Beispiel: *"Mach mir mit Lemo-Opuscar einen Film von rund 40 Sekunden. Stil: 16-bit Pixel RPG. Idee: …"*

**Nicht** `claude plugin marketplace add lemomo-ai/lemo-opuscar` verwenden. Das wäre die Upstream-Version mit Auto-Update und ohne diese Härtung.

## Wer verbindet sich wohin

| Aktion | Ziel | Gesichert durch |
|---|---|---|
| `deps` (npm) | registry.npmjs.org | `package-lock.json` (Integrity), `--ignore-scripts` |
| `deps` (Chromium) | Playwright-CDN | festgelegte Playwright-Version (TLS, kein eigener Hash) |
| `deps` (Python) | PyPI | `--require-hashes --only-binary=:all:` |
| `deps voice` / `tools/fetch.sh` | github.com/lemomo-ai (Release `assets`) | SHA256 in `tools/assets.json`, sicherer Tar-Filter |
| `asr_check.py` (erster Lauf) | huggingface.co | nicht gepinnt (nur Voice-Stufe) |
| `tts_zh.py` | Microsoft Edge-TTS | Text verlässt den Rechner (nur wenn du es benutzt) |
| Rendern (Chrome) | nur 127.0.0.1 | Request-Sperre in `core/render/page.mjs` |

## Sicher arbeiten

- Arbeitsordner ohne Zugangsdaten (kein SSH-Key, keine `.env`, keine Kundenrepos) und keine Secrets in der Umgebung.
- In Claude Code keine pauschalen Berechtigungen für Shell und Netzwerk. Lies, was freigegeben wird.
- `python3 tools/audit.py` vor jedem Start. Nach jeder Änderung an diesem Repo: durchsehen, dann `--update`.
- Fremdes Material (Web-Texte, Dokumente) vor dem Einspeisen ansehen: Es kann den Agenten beeinflussen.
- Für maximale Trennung: in einer VM oder einem Container arbeiten.

## Was fehlt gegenüber Upstream

Galerie, Poster, Demo-Medien, Maintainer-Werkzeuge und 147 Demo-Dateien mit Downloads oder Shell-Code (Liste: `tools/REMOVED-FILES.txt`). Die 8 Dokumentar-Stile sowie Satellite Briefing und LiDAR Survey brauchen deshalb **dein eigenes Material**.

## Lizenz

MIT, Copyright (c) 2026 LemoLab. Die Datei `LICENSE` ist unverändert übernommen und muss erhalten bleiben. Die Änderungen dieser Kopie stehen in `SECURITY-AUDIT.md`.
