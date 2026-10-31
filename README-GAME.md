# Scam or Legit? - install guide

Nothing in your project is overwritten except three small in-place edits
(api.py, App.jsx, AppLayout.jsx) made by the installer script.

## Install (PowerShell)

1. Unzip this folder next to your project, or anywhere.
2. Go to your project root (the folder that contains api.py):

       cd "C:\path\to\Hackathon-MindFlayers"

3. Copy the zip contents into it (adjust the path to where you unzipped):

       Copy-Item -Recurse -Force "C:\path\to\scam-or-legit-update\*" .

4. Run the installer (use the same Python as your venv):

       python apply_game_update.py

   It should print three "added" lines and "All done".
5. Restart the backend (.\start-backend.bat) and open http://localhost:5173/play
6. Optional check:  python -m unittest test_game

## Files added
- game_cards.py     21 hand-written cards (12 scam, 9 legit)
- game_service.py   picks the daily / practice round
- test_game.py      tests
- fincoach/src/pages/Play.jsx, play.css, services/gameService.js
- apply_game_update.py  (installer, can be deleted afterwards)

## If the installer says "NEEDS YOUR ATTENTION"
Do the listed manual step. They are only:
- api.py: add the /api/game/round endpoint (copy the ENDPOINT block from apply_game_update.py)
- App.jsx: import Play and add <Route path="/play" element={<Play />} />
- AppLayout.jsx: add Gamepad2 to the lucide-react import and a NavLink to /play
