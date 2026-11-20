---
name: computer-use-linux
description: >
  See and control this desktop (Linux, Windows or macOS) and the terminals open on it: list every
  window, read a window's UI tree and press buttons by name, take a screenshot
  and click/scroll/drag on it, type text, press shortcuts, and read or type
  into terminals that are already running (other CLI agents, ssh, builds).
  Use when asked to operate a GUI app, check what is on screen, or watch and
  drive another terminal session. Works from any harness that can run a shell
  command.
---

# Computer Use Linux — desktop + terminal control

Every command is `computer-use-linux ...`. Add `--json` anywhere for machine output.

## 1. Look first
```bash
computer-use-linux observe          # every window (ref win:{...}) + every open terminal
computer-use-linux caps             # what works on this machine (input, windows, terminals)
```
If `caps` says something needs approval, run `computer-use-linux setup` once:
- Linux Wayland: tell the user to press **Share** (with "Allow restoring"
  ticked) on the remote-control dialog. After that it never asks again.
- macOS: tell the user to allow the terminal/Python under System Settings →
  Privacy & Security → **Accessibility** and **Screen Recording**.
- Windows and X11 need no approval.

## Be fast: fewer round trips
Every separate command costs you a full model turn. Plan the steps you already
know and send them in ONE call; check once at the end with `--after`:
```bash
computer-use-linux do 'click-text "New"' 'fill @s7k2m9qx:e9 "report.txt" --enter' \
             'wait --element "Saved"' --after
computer-use-linux click @s7k2m9qx:e4 --after       # act + see what changed (new refs included)
computer-use-linux click-text "Save"                # find by name and press: one read, one call
computer-use-linux wait --element "Done" --timeout 15   # instead of sleep + re-read loops
```
`do` stops at the first failing step and says which one. `--after` prints
`+` new elements (with refs), `-` gone, `~` changed values — no separate
`tree`/`screenshot` needed to verify. Refs stay valid after the UI changes
(they are matched by identity, not position), so keep using them.
Prefer `tree -i` over screenshots: text is faster to read than an image.

## 2. Act on GUI apps — structure first, pixels second
```bash
computer-use-linux tree --window win:{...}          # snapshot; actionable lines end in ref=@s7k2m9qx:e4
computer-use-linux tree --window win:{...} -i       # only actionable elements (shorter)
computer-use-linux tree --root @s7k2m9qx:e3 -i      # drill into one region of a dense app
computer-use-linux click @s7k2m9qx:e4               # press it; the user's mouse does not move
computer-use-linux find "Save" --window win:{...}   # search by name/value → refs
computer-use-linux set-text @s7k2m9qx:e9 "text"     # replace a field's content
```
`tree` leaves out closed menus and folds unnamed layout boxes, so what you
read is what is on screen. Content scrolled out of view may be missing:
scroll, then read again.

Refs belong to the snapshot that printed them. Before every action the
element is re-identified by window, role, name and named ancestors — never
by position — so a ref keeps hitting the same button after the UI shifts.
If it cannot be proven, the action is refused and nothing is pressed:
`STALE_REF` (element gone / changed) or `AMBIGUOUS_TARGET` (now matches
several) → take a new `tree` and use its refs. A disabled element is waited
for up to 5 s (`CUL_WAIT`), then `TIMEOUT`. Loop: tree → act → tree
to verify.

Electron/Chromium apps (Discord, Vesktop, VS Code, Slack, Chrome) publish an
empty tree unless started with a flag; `tree` then ends with a `#` hint line.
```bash
computer-use-linux launch vesktop                   # starts it with the flag → win:{...}
computer-use-linux launch code ~/project            # arguments pass through
```
A running single-instance app ignores the flag. Ask the user before closing
their app to relaunch it.

When the app still publishes no tree (games, canvas apps):
```bash
computer-use-linux screenshot                       # monitor of the active window (default)
computer-use-linux screenshot --window win:{...}    # one window: sharpest
computer-use-linux screenshot --region 1080 420 640 360   # zoom: screen x y w h, full detail
computer-use-linux screenshot --screen DP-4 | --screen all  # another monitor / whole desktop
computer-use-linux click 412 230 --from-shot        # pixel coords from THAT image
computer-use-linux click 412 230 --from-shot --right | --double
computer-use-linux scroll 5 --at 600 400            # + down / - up (screen coords)
computer-use-linux drag 100 200 400 200             # screen coords
```
The user's pointer is moved back where it was right after each click.
A screenshot takes ~0.1 s. On several monitors `--screen all` shrinks text
until it is unreadable: look at one monitor, a window or a region instead.
Text too small? Take a `--region` around it rather than guessing.

Show the user where you are working with your OWN visible pointer (a second
arrow; it never moves their mouse or takes clicks):
```bash
computer-use-linux point <ref>                      # glide to the element, ring, then press it
computer-use-linux cursor 412 230 [--click]         # screen coords; --click only shows a ring
computer-use-linux cursor-hide
```

## 3. Keyboard
```bash
computer-use-linux window win:{...} activate        # focus the target window first
computer-use-linux type "Merhaba dünya"             # any language, newlines ok
computer-use-linux key ctrl+s | Return | alt+F4 | ctrl+shift+t
```
On macOS use `cmd` for the Command key (`cmd+s`, `cmd+v`); `ctrl` is Control.

## 4. Terminals already open on the desktop
```bash
computer-use-linux terms                            # refs: konsole:… tmux:… wincon:PID terminal:… iterm:…
computer-use-linux term-read konsole:7891:2         # what that terminal shows right now
computer-use-linux term-send konsole:7891:2 "git status" --enter
computer-use-linux term-send konsole:7891:2 --key C-c          # Enter, C-c, C-d, Esc, Up, Tab...
```
`program` tells you what runs in the foreground (claude, vim, ssh, bash).
Read again after sending: output takes time; poll `term-read` until it settles.

## 5. Your own scratch terminal
```bash
computer-use-linux run "pytest -q" --session build  # runs, waits, returns output + exit code
computer-use-linux screen --session build           # read it later (sessions persist)
computer-use-linux keys C-c --session build
computer-use-linux cleanup                          # close only the sessions you created
```

## 6. Several agents on one desktop
When more than one agent (sub-agents, parallel sessions) drives this desktop,
give EVERY command its own name with `--agent NAME`:
```bash
computer-use-linux --agent research screenshot
computer-use-linux --agent research click @s7k2m9qx:e4
computer-use-linux --agent writer type "..."
```
Each name gets its own pointer in its own colour (a Material Bibata cursor
variant when installed, so the user sees who works where), its own
background service (one agent's `wait`/`do` does not stall the others), its
own last screenshot for `--from-shot`, and its own default `run` session.
Reading (`tree`, `find`, `screenshot`, `term-read`) runs fully in parallel.
Clicks and keystrokes go out one at a time machine-wide — there is one real
pointer and one keyboard focus. Never `window ... activate` and then `type`
as two commands: another agent can take focus in between. Name the window
in the same command instead:
```bash
computer-use-linux --agent writer type "metin" --window win:{...}
computer-use-linux --agent writer key ctrl+s --window win:{...}
```
`CUL_AGENT=NAME` works too.

## Rules
- Verify what matters, cheaply: `--after` on the last action of a `do` batch,
  `term-read` for terminals. Do not assume — but do not spend a turn per click either.
- Activate the window before `type`/`key`; keystrokes go to the focused window.
- Closing windows, sending to someone's terminal, or typing into a shell is
  real and visible to the user. Say what you are about to do when it matters.
