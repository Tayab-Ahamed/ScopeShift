"""Build the 8-slide ScopeShift Phase 2 selection deck."""
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

BG, PANEL, LINE = "0B1020", "151C33", "2A3558"
TEXT, MUTED = "F8FAFC", "94A3B8"
AMBER, GREEN, RED, BLUE = "F59E0B", "22C55E", "EF4444", "60A5FA"
FONT = "Calibri"


def rgb(h):
    return RGBColor.from_string(h)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def new_slide(n, title=None, kicker=None, is_appendix=False):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = rgb(BG)
    if kicker:
        text(s, kicker.upper(), 0.7, 0.45, 8, 0.4, 13, MUTED, bold=True)
    if title:
        text(s, title, 0.7, 0.8, 11.9, 1.0, 34, TEXT, bold=True)
    footer_text = "ScopeShift  |  Enterprise Edition  |  Appendix" if is_appendix else f"ScopeShift  |  Enterprise Edition  |  {n}/8"
    text(s, footer_text, 0.7, 7.0, 6, 0.3, 11, MUTED)
    return s


def text(s, t, x, y, w, h, size=18, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, italic=False):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = Inches(0.05)
    lines = t if isinstance(t, list) else [t]
    for i, ln in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        r = p.add_run()
        r.text = ln
        r.font.size, r.font.bold, r.font.italic = Pt(size), bold, italic
        r.font.name = FONT
        r.font.color.rgb = rgb(color)
        if i:
            p.space_before = Pt(size * 0.4)
    return tb


def box(s, x, y, w, h, fill=PANEL, line=LINE, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.25):
    b = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        b.adjustments[0] = 0.06
    b.fill.solid()
    b.fill.fore_color.rgb = rgb(fill)
    if line:
        b.line.color.rgb = rgb(line)
        b.line.width = Pt(lw)
    else:
        b.line.fill.background()
    b.shadow.inherit = False
    return b


def card(s, x, y, w, h, head, body, accent=BLUE, head_size=20, body_size=15):
    box(s, x, y, w, h)
    box(s, x, y, 0.09, h, fill=accent, line=None, shape=MSO_SHAPE.RECTANGLE)
    text(s, head, x + 0.3, y + 0.15, w - 0.5, 0.5, head_size, TEXT, bold=True)
    text(s, body, x + 0.3, y + 0.75, w - 0.5, h - 0.9, body_size, MUTED)


def arrow(s, x, y, w=0.45, color=MUTED):
    a = s.shapes.add_shape(MSO_SHAPE.RIGHT_ARROW, Inches(x), Inches(y), Inches(w), Inches(0.35))
    a.fill.solid()
    a.fill.fore_color.rgb = rgb(color)
    a.line.fill.background()


def flow(s, steps, y, h=1.0, color=BLUE, size=15, x0=0.7, total=11.9, gap=0.5, colors=None):
    n = len(steps)
    w = (total - gap * (n - 1)) / n
    for i, st in enumerate(steps):
        x = x0 + i * (w + gap)
        c = colors[i] if colors else color
        box(s, x, y, w, h, fill=PANEL, line=c, lw=2)
        text(s, st, x + 0.05, y, w - 0.1, h, size, TEXT, bold=True, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        if i < n - 1:
            arrow(s, x + w + (gap - 0.35) / 2, y + h / 2 - 0.17, 0.35, MUTED)


# 1 - Title / hook
s = new_slide(1)
text(s, "ENTERPRISE  |  EVIDENCE-GOVERNED BRD GENERATOR", 0.7, 1.2, 10, 0.4, 14, AMBER, bold=True)
text(s, "ScopeShift", 0.7, 1.7, 11, 1.6, 80, TEXT, bold=True)
text(s, "From conflicting evidence to governed requirements.", 0.7, 3.4, 11.5, 0.7, 28, MUTED)
box(s, 0.7, 4.8, 11.9, 1.3, fill=PANEL, line=AMBER, lw=2)
text(s, "\u201cSeeing a button is not approving the button.\u201d", 0.9, 4.8, 11.5, 1.3, 34, AMBER,
     bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# 2 - Problem
s = new_slide(2, "One checkout feature. Three sources. Three answers.", "The problem")
srcs = [
    ("BRD", "UPI only", "\u201cCheckout shall support UPI payments only.\u201d", BLUE),
    ("Screenshot", "Card button visible", "A UI observation. Nobody approved it.", AMBER),
    ("Client note", "Card in scope, UPI to Phase 2", "\u201cCheckout shall support Card payments. UPI moves to Phase 2.\u201d", GREEN),
]
for i, (h, big, sub, c) in enumerate(srcs):
    x = 0.7 + i * 4.05
    box(s, x, 2.1, 3.8, 2.9, line=c, lw=2)
    text(s, h.upper(), x + 0.25, 2.25, 3.3, 0.4, 14, c, bold=True)
    text(s, big, x + 0.25, 2.75, 3.3, 1.0, 26, TEXT, bold=True)
    text(s, sub, x + 0.25, 3.85, 3.3, 1.0, 15, MUTED, italic=True)
text(s, "AI can extract all three facts. The hard part is deciding what is allowed to become a requirement.",
     0.7, 5.5, 11.9, 1.0, 26, TEXT, bold=True)

# 3 - Why current AI fails
s = new_slide(3, "Today\u2019s AI picks an answer. Nobody can audit it.", "Why current AI fails")
flow(s, ["Documents", "LLM summary", "\u201cCard is supported\u201d"], 1.9, 1.0,
     colors=[BLUE, AMBER, RED], size=20)
fails = [
    ("Observation becomes approval", "A visible button is treated as a decision."),
    ("Provenance is lost", "No link from the answer back to its source."),
    ("No explanation of change", "Cannot say what changed, or why."),
    ("No safe undo", "A withdrawn decision stays baked into the summary."),
]
for i, (h, b) in enumerate(fails):
    x = 0.7 + (i % 2) * 6.05
    y = 3.4 + (i // 2) * 1.7
    card(s, x, y, 5.85, 1.5, h, b, accent=RED, head_size=19, body_size=15)

# 4 - Solution
s = new_slide(4, "Gemini extracts the evidence. Code decides the authority.", "Our solution")
flow(s, ["Evidence", "Citation validation", "Append-only event log", "Deterministic resolver", "Current BRD"],
     2.0, 1.2, size=16, gap=0.35, colors=[BLUE, BLUE, BLUE, GREEN, GREEN])
card(s, 0.7, 3.8, 5.85, 2.3, "Gemini = extractor",
     ["Reads PDF, screenshot and note.", "Returns structured claims constrained to a fixed schema.",
      "Never assigns source IDs. Never grants authority."], accent=BLUE, body_size=16)
card(s, 6.75, 3.8, 5.85, 2.3, "Code = authority",
     ["A requirement is promoted only if the client note", "explicitly changes scope and its quote is verified.",
      "Screenshots can never grant authority."], accent=GREEN, body_size=16)

# 5 - Demo
s = new_slide(5, "DISPUTED \u2192 GOVERNED \u2192 DISPUTED", "The winning demo")
beats = [
    ("BEAT 1", "DISPUTED", AMBER, "BRD and screenshot conflict.", "Requirement withheld."),
    ("BEAT 2", "GOVERNED", GREEN, "Client note explicitly authorizes Card.", "Requirement enters the BRD with its source."),
    ("BEAT 3", "DISPUTED", AMBER, "Client decision is withdrawn.", "Requirement disappears. The reason stays visible."),
]
for i, (b, st, c, l1, l2) in enumerate(beats):
    x = 0.7 + i * 4.05
    box(s, x, 2.0, 3.8, 4.4, line=c, lw=3)
    text(s, b, x + 0.25, 2.15, 3.3, 0.4, 14, MUTED, bold=True)
    text(s, st, x + 0.25, 2.65, 3.3, 0.9, 38, c, bold=True)
    text(s, [l1, l2], x + 0.25, 3.85, 3.3, 2.3, 18, TEXT)
text(s, "Live Interactive Cockpit: 3D Spatial Topology Matrix (Three.js) \u2022 Live SSE Evidence Feed \u2022 Time-Travel Scrubber \u2022 Ask-the-Evidence Q&A \u2022 Contradiction Heatmap \u2022 Automated Simulation Walkthrough",
     0.7, 6.5, 11.9, 0.4, 13, BLUE, bold=True)

# 6 - Technical
s = new_slide(6, "Four blocks. One accountable pipeline.", "How it works technically")
blocks = [
    ("Gemini structured extraction (Vertex AI route)", "Claims constrained to an enum of claim IDs, with quote and proposed scope change. Vertex AI endpoint when GOOGLE_CLOUD_PROJECT is set; deterministic fallback offline.", BLUE),
    ("Code-level quote and schema validation", "Quotes must exist in the source text. Screenshots can never govern. Hallucinated claims are rejected; chaos attacks are executed, not scripted.", BLUE),
    ("BigQuery append-only event log (env-gated)", "ADDED and REMOVED events streamed to BigQuery when credentials exist; SQLite is the persisted local mirror. Insert-only by application design.", GREEN),
    ("Live SSE feed + deterministic resolver", "Evidence streams in real time; resolve(claim_id, active_evidence) recomputes live. Citation integrity is fail-closed: dangling citations refuse to serve.", GREEN),
]
for i, (h, b, c) in enumerate(blocks):
    x = 0.7 + (i % 2) * 6.05
    y = 1.9 + (i // 2) * 2.0
    card(s, x, y, 5.85, 1.85, h, b, accent=c, head_size=19, body_size=15)
box(s, 0.7, 6.0, 11.9, 0.8, fill=PANEL, line=AMBER, lw=1.5)
text(s, "Cloud integrations are env-gated: the demo runs fully offline on the local mirror; with GCP credentials it streams to BigQuery / Cloud Storage / Vertex AI.",
     0.8, 6.0, 11.7, 0.8, 18, AMBER, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# 7 - Differentiation table
s = new_slide(7, "A requirements system, not a document summarizer.", "What makes ScopeShift different")
rows = [
    ("Typical AI document tool", "ScopeShift"),
    ("Summarizes documents", "Produces governed requirements"),
    ("Trusts model judgment", "Separates extraction from authority"),
    ("Loses provenance", "Every requirement has validated citations"),
    ("Overwrites the current answer", "Replays an append-only history"),
    ("Hard to undo", "Withdrawal recomputes the current BRD"),
]
tbl = s.shapes.add_table(len(rows), 2, Inches(0.7), Inches(1.9), Inches(11.9), Inches(4.5)).table
tbl.columns[0].width, tbl.columns[1].width = Inches(5.6), Inches(6.3)
for r, (a, b) in enumerate(rows):
    for c, val in enumerate((a, b)):
        cell = tbl.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(LINE if r == 0 else PANEL)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.25)
        p = cell.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = val
        run.font.name, run.font.size = FONT, Pt(20 if r else 18)
        run.font.bold = r == 0 or c == 1
        run.font.color.rgb = rgb(MUTED if (c == 0 and r) else (GREEN if (c == 1 and r) else TEXT))

# 8 - Build plan
s = new_slide(8, "Built, tested, and demo-ready.", "Build status")
steps = ["Multi-claim extraction + validation", "BigQuery/GCS/Vertex env-gated integrations", "Live SSE evidence feed",
         "Deterministic resolver + fail-closed citations", "Ask-the-evidence + heatmap + 3D twin", "90 automated tests green"]
for i, st in enumerate(steps):
    x = 0.7 + (i % 3) * 4.05
    y = 1.9 + (i // 3) * 1.55
    box(s, x, y, 3.8, 1.3)
    text(s, "\u2713", x + 0.2, y, 0.6, 1.3, 32, GREEN, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, st, x + 0.85, y, 2.85, 1.3, 17, TEXT, bold=True, anchor=MSO_ANCHOR.MIDDLE)
box(s, 0.7, 5.3, 11.9, 1.4, fill=PANEL, line=GREEN, lw=2)
text(s, "ScopeShift turns AI from a requirements guesser into an accountable requirements system.",
     0.9, 5.3, 11.5, 1.4, 26, TEXT, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

# 9 - Appendix: SIMULATED baseline experiment (honest labeling)
s = new_slide(9, "Baseline: SIMULATED model stand-in \u2014 live Gemini run pending", "Appendix: Baseline", is_appendix=True)
box(s, 0.7, 1.55, 3.4, 0.55, fill=PANEL, line=RED, lw=2)
text(s, "\u26a0 SIMULATED \u2014 NOT MEASURED ON GEMINI", 0.8, 1.55, 3.2, 0.55, 15, RED, bold=True,
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, "mock-gemini-preview stand-in \u2022 5 runs per condition \u2022 API-default temperature \u2022 source: baseline_out/*/summary.md (unedited). Live 10-run Gemini baseline runs on the stage laptop with GEMINI_API_KEY.",
     4.4, 1.55, 8.2, 0.6, 14, MUTED)

base_rows = [
    ("Condition", "Test A (note present)", "Test B (screenshot only)", "Citations"),
    ("Plain (simulated)", "5/5 Card settled", "0/5 correct \u2014 5/5 settled Card from the UI button", "0 valid / 5 unverifiable"),
    ("Hinted (simulated)", "5/5 Card settled", "5/5 conflict flagged", "5 valid / 0 unverifiable"),
    ("ScopeShift (deterministic)", "GOVERNED on every replay", "DISPUTED on every replay \u2014 withheld", "Code-verified \u2022 fail-closed"),
]
t9 = s.shapes.add_table(len(base_rows), 4, Inches(0.7), Inches(2.3), Inches(11.9), Inches(3.0)).table
t9.columns[0].width = Inches(3.2)
t9.columns[1].width = Inches(2.6)
t9.columns[2].width = Inches(3.8)
t9.columns[3].width = Inches(2.3)
for r, row in enumerate(base_rows):
    for c, val in enumerate(row):
        cell = t9.cell(r, c)
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(LINE if r == 0 else (PANEL if r < 3 else "1A284A"))
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.margin_left = Inches(0.15)
        p = cell.text_frame.paragraphs[0]
        run = p.add_run()
        run.text = val
        run.font.name, run.font.size = FONT, Pt(14 if r else 13)
        run.font.bold = r == 0 or r == 3 or c == 0
        run.font.color.rgb = rgb(TEXT if r == 0 else (GREEN if r == 3 else (AMBER if (c == 2 and r == 1) else MUTED)))

box(s, 0.7, 5.6, 11.9, 1.1, fill=PANEL, line=BLUE, lw=1.5)
text(s, "Takeaway: even simulated, the unhinted model treats the visible button as authority 5/5 in Test B.\nScopeShift withholds the requirement deterministically \u2014 proven by 90 automated tests, not by model luck.",
     0.9, 5.6, 11.5, 1.1, 16, TEXT, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

out = "submission/ScopeShift-HackSprint-Phase2-8slide.pptx"
prs.save(out)
print("saved", out)
