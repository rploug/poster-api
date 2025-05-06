# app.py
from flask import Flask, render_template, request, send_file
from PIL import Image, ImageDraw, ImageFont, ImageOps
import os, math, textwrap, tempfile, glob, uuid, random

app = Flask(__name__)
UPLOAD_FOLDER = tempfile.mkdtemp()
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------- paths ---------------------------------------------------
BASE_DIR     = os.path.join(os.path.dirname(__file__), "static")
FONT_BOLD    = os.path.join(BASE_DIR, "BROWN-BOLD.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "BROWN-REGULAR.ttf")
FONT_LIGHT    = os.path.join(BASE_DIR, "BROWN-LIGHT.ttf")
LOGO_BLACK   = os.path.join(BASE_DIR, "logoBlack.png")
LOGO_WHITE   = os.path.join(BASE_DIR, "logoWhite.png")

# -------- helpers -------------------------------------------------
def safe_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()

# -------- poster generator ---------------------------------------
def make_poster(config, img_paths, out_path):
    dpi = 300
    mm_to_inch = 1 / 25.4
    W = int(420 * mm_to_inch * dpi)
    H = int(297 * mm_to_inch * dpi)
    COLLAGE_H = int(W * 9 / 16)
    GAP = int(dpi * 0.1)

    canvas = Image.new("RGB", (W, H), config["bg"])
    draw   = ImageDraw.Draw(canvas)

    n = len(img_paths)

    # --- decide grid for exactly two images -----------------------
    if n == 2:
        ratios = []
        for p in img_paths[:2]:
            with Image.open(p) as im:
                ratios.append(im.width / im.height)  # >1 ⇒ landscape
        # both portrait  -> stack; otherwise side‑by‑side
        rows, cols = (2, 1) if ratios[0] < 1 and ratios[1] < 1 else (1, 2)
    else:
        rows = max(1, round(math.sqrt(n / (W / COLLAGE_H))))
        cols = math.ceil(n / rows)

    # --- place images (order already shuffled) --------------------
    idx, y = 0, GAP
    for r in range(rows):
        cols_in_row = min(cols, n - idx)
        cell_w = (W - GAP * (cols_in_row + 1)) // cols_in_row
        cell_h = (COLLAGE_H - GAP * (rows + 1)) // rows
        if r == rows - 1:
            cell_h = COLLAGE_H - y - GAP
        x = GAP
        for _ in range(cols_in_row):
            img = Image.open(img_paths[idx]).convert("RGB")
            img = ImageOps.fit(img, (cell_w, cell_h), Image.LANCZOS, centering=(0.5, 0.5))
            canvas.paste(img, (x, y))
            x += cell_w + GAP
            idx += 1
        y += cell_h + GAP

    # --- footer ---------------------------------------------------
    footer_y = COLLAGE_H + GAP * 2
    ft_title = safe_font(config["font_title"], int(dpi * 0.50))
    ft_body  = safe_font(config["font_body"],  int(dpi * 0.22))
    ft_small = safe_font(config["font_small"], int(dpi * 0.19))

    draw.text((GAP * 3, footer_y), config["project"], font=ft_title, fill=config["fg"])

    wrapped = "\n".join(textwrap.wrap(config["description"], width=100))
    draw.multiline_text((GAP * 3, footer_y + int(dpi * 0.55)),
                        wrapped, font=ft_body, fill=config["fg"],
                        spacing=int(dpi * 0.09))

    authors_display = ", ".join(config["authors"][:-1]) + " & " + config["authors"][-1]
    draw.multiline_text((GAP * 3, footer_y + int(dpi * 1.6)),
                        f"{config['semester']} - {config['course']}\n{authors_display}",
                        font=ft_small, fill=config["fg"],
                        spacing=int(dpi * 0.07))

    # --- logo -----------------------------------------------------
    logo = Image.open(config["logo"]).convert("RGBA")
    w0, h0 = logo.size
    max_h  = int((H - footer_y - GAP * 2) // 1.5)
    logo   = logo.resize((int(w0 * max_h / h0), max_h), Image.LANCZOS)
    lx, ly = int(W - GAP - logo.width * 1.17), int(H - GAP - logo.height * 1.3)
    canvas.paste(logo, (lx, ly), logo)

    canvas.save(out_path, dpi=(dpi, dpi))

# -------- routes --------------------------------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # save uploads & randomise order
        img_paths = []
        for f in request.files.getlist('images'):
            fname = os.path.join(UPLOAD_FOLDER, f"{uuid.uuid4().hex}_{f.filename}")
            f.save(fname)
            img_paths.append(fname)
        random.shuffle(img_paths)

        # --- form values ------------------------------------------
        title_raw = request.form['project_name'][:40]
        desc_raw  = request.form['description'][:290]

        selected_course = request.form.get('course', '').strip()
        custom_course   = request.form.get('course_custom', '').strip()
        course_final    = (custom_course or selected_course).title()

        cfg = {
            "project":     title_raw.title(),
            "description": desc_raw.strip().capitalize(),
            "semester":    request.form['semester'],
            "course":      course_final,
            "authors":     [a.strip().title() for a in request.form['authors'].split(',')],
            "bg":   ("black" if request.form.get('dark') else "white"),
            "fg":   ("white" if request.form.get('dark') else "black"),
            "logo": (LOGO_WHITE if request.form.get('dark') else LOGO_BLACK),
            "font_title": FONT_BOLD,
            "font_body":  FONT_REGULAR,
            "font_small": FONT_LIGHT,
        }

        out_path = os.path.join(UPLOAD_FOLDER, f"poster_{uuid.uuid4().hex}.png")
        make_poster(cfg, img_paths, out_path)
        download_filename = f"SDU Project Poster - {cfg['project']}.png"

        return send_file(out_path, as_attachment=True, download_name=download_filename)

    return render_template('index.html')

if __name__ == "__main__":
    app.run(debug=True)
