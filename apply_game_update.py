"""Installs the "Scam or Legit?" game into the FinCoach project.

Run once from the project root (the folder that contains api.py):

    python apply_game_update.py

It edits three existing files in place (api.py, App.jsx, AppLayout.jsx) without
touching your other changes, and it is safe to run twice. The new files in this
zip must already be copied into the project (same folder structure).
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
manual = []


def read(p):
    if not p.exists():
        return None
    with open(p, encoding="utf-8", newline="") as f:  # newline="" keeps Windows line endings
        return f.read()


def write(p, text):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def report(name, state, hint=None):
    print(f"  {name}: {state}")
    if hint:
        manual.append(f"{name}: {hint}")


# ------------------------------------------------------------------ api.py
ENDPOINT = '''


# ==============================================================================
# GAME: "Scam or Legit?"
# ==============================================================================


@app.get("/api/game/round", tags=["Game"])
async def get_game_round(mode: str = "daily"):
    """Cards for one round of Scam or Legit. mode: daily (same for everyone today) or practice (random)."""
    import game_service

    try:
        return game_service.build_round(mode)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
'''

p = ROOT / "api.py"
s = read(p)
if s is None:
    report("api.py", "NOT FOUND", "run this script from the folder that contains api.py")
elif "/api/game/round" in s:
    report("api.py", "already updated")
else:
    nl = "\r\n" if "\r\n" in s else "\n"
    write(p, s.rstrip() + ENDPOINT.replace("\n", nl))
    report("api.py", "game endpoint added")

# ------------------------------------------------------------------ App.jsx
p = ROOT / "fincoach" / "src" / "App.jsx"
s = read(p)
if s is None:
    report("App.jsx", "NOT FOUND", "expected at fincoach/src/App.jsx")
elif "pages/Play.jsx" in s:
    report("App.jsx", "already updated")
else:
    new = s
    if "import News from './pages/News.jsx'" in new:
        new = new.replace("import News from './pages/News.jsx'", "import News from './pages/News.jsx'; import Play from './pages/Play.jsx'", 1)
    else:
        new = new.replace("import AppLayout", "import Play from './pages/Play.jsx'\nimport AppLayout", 1)
    anchor = '<Route path="/expenses" element={<Expenses />} />'
    if "<News />" in new:
        anchor = '<Route path="/news" element={<News />} />'
    new = new.replace(anchor, anchor + '<Route path="/play" element={<Play />} />', 1)
    if "pages/Play.jsx" in new and 'path="/play"' in new:
        write(p, new)
        report("App.jsx", "play route added")
    else:
        report("App.jsx", "could not patch", "add `import Play from './pages/Play.jsx'` and `<Route path=\"/play\" element={<Play />} />` next to the other routes")

# ------------------------------------------------------------------ AppLayout.jsx
p = ROOT / "fincoach" / "src" / "layouts" / "AppLayout.jsx"
s = read(p)
if s is None:
    report("AppLayout.jsx", "NOT FOUND", "expected at fincoach/src/layouts/AppLayout.jsx")
elif 'to="/play"' in s:
    report("AppLayout.jsx", "already updated")
else:
    new = s
    if "Gamepad2" not in new:
        new = re.sub(r"(import \{[^}]*)(\} from 'lucide-react')", lambda m: m.group(1).rstrip() + ", Gamepad2 " + m.group(2), new, count=1)
    link = '<NavLink to="/play" className="nav"><Gamepad2 size={18} /><span>Play</span></NavLink>'
    m = re.search(r'<NavLink to="/news"[^\n]*?</NavLink>', new) or re.search(r'<NavLink to="/expenses"[^\n]*?</NavLink>', new)
    if m:
        indent = re.search(r"([ \t]*)<NavLink to=\"/(news|expenses)\"", new).group(1)
        nl = "\r\n" if "\r\n" in new else "\n"
        new = new[: m.end()] + nl + indent + link + new[m.end():]
    if 'to="/play"' in new and re.search(r"import \{[^}]*Gamepad2[^}]*\} from 'lucide-react'", new):
        write(p, new)
        report("AppLayout.jsx", "Play menu link added")
    else:
        report("AppLayout.jsx", "could not patch", "import Gamepad2 from lucide-react and add " + link + " in the sidebar")

# ------------------------------------------------------------------ new files present?
needed = ["game_cards.py", "game_service.py", "test_game.py", "fincoach/src/pages/Play.jsx",
          "fincoach/src/pages/play.css", "fincoach/src/services/gameService.js"]
missing = [n for n in needed if not (ROOT / n).exists()]
if missing:
    manual.append("these new files are missing, copy them from the zip: " + ", ".join(missing))

print()
if manual:
    print("NEEDS YOUR ATTENTION:")
    for m in manual:
        print("  -", m)
    sys.exit(1)
print("All done. Restart the backend, then open http://localhost:5173/play")
