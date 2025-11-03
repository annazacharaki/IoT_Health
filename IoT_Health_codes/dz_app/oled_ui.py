# oled_ui.py
import os, time, threading, textwrap
os.environ.setdefault("LUMA_NO_EXIT", "1")

from luma.core.interface.serial import i2c
from luma.oled.device import ssd1306
from luma.core.render import canvas
from PIL import ImageFont

# --- device ---
serial = i2c(port=1, address=0x3C)
device = ssd1306(serial, width=128, height=64)

# --- fonts ---
try:
    FONT_TITLE = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
    FONT_BODY  = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
except:
    FONT_TITLE = ImageFont.load_default()
    FONT_BODY  = ImageFont.load_default()

# --- state / sync ---
_state_lock = threading.Lock()
_state = {
    "title": "",
    "lines": ["", ""],
    "show_progress": False,
}

_anim_thread = None
_anim_running = False

def _wrap_two_lines(body_text: str, max_chars: int = 21):
    # απλή, σταθερή περιτύλιξη ~21 chars/γραμμή για 128px πλάτος με μέγεθος 12
    wrapped = textwrap.wrap(body_text, width=max_chars)
    return (wrapped + ["", ""])[:2]

def _render_frame(draw, pos):
    # τίτλος (γραμμή 1)
    draw.text((0, 0), _state["title"], font=FONT_TITLE, fill=255)
    # body (γραμμές 2–3)
    y = 18
    for line in _state["lines"]:
        draw.text((0, y), line, font=FONT_BODY, fill=255)
        y += 14
    # progress (γραμμή 4)
    if _state["show_progress"]:
        bar_w = 20
        # μπάρα τύπου KITT
        draw.rectangle((pos, 52, pos + bar_w, 62), outline=255, fill=255)

def _anim_loop():
    global _anim_running
    width = device.width
    step = 10        # ↑ πιο γρήγορο (ήταν ~5)
    sleep_s = 0.05   # ↑ πιο γρήγορο (ήταν ~0.10)
    bar_w = 20

    pos = 0
    direction = 1
    while _anim_running:
        with _state_lock:
            with canvas(device) as draw:
                _render_frame(draw, pos)
        pos += direction * step
        if pos <= 0 or pos + bar_w >= width:
            direction *= -1
        time.sleep(sleep_s)

def display_message(title: str, body: str, show_progress: bool):
    """
    Γράφει στην OLED:
      - title:    1η γραμμή (τίτλος)
      - body:     κείμενο με wrap για 2η–3η γραμμή
      - show_progress: True/False → μπάρα τύπου KITT στη 4η γραμμή
    Καθαρίζει την οθόνη στην αρχή της κλήσης.
    """
    global _anim_thread, _anim_running

    # ετοιμάζουμε νέο state
    lines = _wrap_two_lines(body, max_chars=21)

    with _state_lock:
        _state["title"] = title or ""
        _state["lines"] = lines
        _state["show_progress"] = bool(show_progress)
        device.clear()

    # αν δεν θέλουμε animation → ζωγραφίζουμε 1 φορά και τελειώσαμε
    if not show_progress:
        with _state_lock:
            with canvas(device) as draw:
                _render_frame(draw, pos=0)
        # σταμάτα τυχόν παλιό animation
        if _anim_running:
            _anim_running = False
            if _anim_thread and _anim_thread.is_alive():
                _anim_thread.join(timeout=0.5)
        return

    # θέλουμε animation
    if _anim_running and _anim_thread and _anim_thread.is_alive():
        # ήδη τρέχει → δεν χρειάζεται νέα εκκίνηση (state άλλαξε, θα αποτυπωθεί στο επόμενο frame)
        return

    # ξεκίνα thread
    _anim_running = True
    _anim_thread = threading.Thread(target=_anim_loop, daemon=True)
    _anim_thread.start()
