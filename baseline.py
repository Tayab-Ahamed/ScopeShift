#!/usr/bin/env python3
"""
ScopeShift baseline: plain Gemini, 10x Test A + 10x Test B.

Fixtures (in --fixtures dir):
  brd.pdf          BRD page ("Checkout accepts UPI only.")
  checkout.png     screenshot with Card button visible
  client_note.txt  contains "Card is in scope. UPI moves to Phase 2."
Optional: brd.txt (extracted BRD text for citation checks; else pypdf is used).

Test A: BRD + screenshot + note
Test B: BRD + screenshot            (note withdrawn)

Each run is an independent single-turn API call (no shared history).
Outputs in --out: runs.jsonl (raw), summary.csv, summary.md (for Slide 4).

pip install google-genai pypdf
export GEMINI_API_KEY=...
python baseline.py --model <current-gemini-model-name> --runs 10
"""
import argparse, csv, json, os, re, sys, time, collections
from pathlib import Path

SCHEMA = """Return JSON only:
{
  "requirement": "<one-sentence requirement>",
  "card_in_scope": true | false | "unclear",
  "citations": [{"source": "brd" | "screenshot" | "client_note", "quote": "<exact text or UI element you relied on>"}]
}

The value of card_in_scope MUST be exactly one of: true, false, "unclear"."""

PROMPTS = {
    # primary baseline: no governance hints
    "plain": """You are given project documents for a merchant checkout feature.
Produce the current payment-method requirement for checkout.
Use only the documents provided. """ + SCHEMA,
    # secondary condition: prompt states the governance rule
    "hinted": """You are given project documents for a merchant checkout feature.
Produce the current payment-method requirement for checkout.

Use only the documents provided. Do not assume that any source has authority
over another source. If the provided evidence conflicts and there is no
explicit client scope decision resolving it, set card_in_scope to "unclear".

""" + SCHEMA,
}

EXPECTED = {"A": "CARD_SETTLED", "B": "FLAGGED_CONFLICT"}


def norm(s):
    s = re.sub(r"[\W_]+", " ", str(s).lower())
    return re.sub(r"\s+", " ", s).strip()


def classify(parsed):
    c = parsed.get("card_in_scope")
    if isinstance(c, str):
        c = c.strip().lower()
        if c in ("true", "yes"):
            c = True
        elif c in ("false", "no"):
            c = False
        else:
            c = "unclear"
    if c is True:
        return "CARD_SETTLED"
    if c is False:
        return "UPI_ONLY_SETTLED"
    return "FLAGGED_CONFLICT"


def check_citations(parsed, texts, provided):
    """valid: quote found in text source. unverifiable: screenshot (only
    existence of source is checkable). invalid: source not provided in this
    test, unknown source, or quote not found in text."""
    v = u = bad = 0
    for c in parsed.get("citations") or []:
        src, q = c.get("source"), norm(c.get("quote", ""))
        if src not in provided or src not in ("brd", "screenshot", "client_note"):
            bad += 1
        elif src == "screenshot":
            u += 1
        elif q and q in norm(texts[src]):
            v += 1
        else:
            bad += 1
    return v, u, bad


def load_text_sources(fx):
    texts = {"client_note": (fx / "client_note.txt").read_text(encoding="utf-8")}
    if (fx / "brd.txt").exists():
        texts["brd"] = (fx / "brd.txt").read_text(encoding="utf-8")
    else:
        from pypdf import PdfReader
        texts["brd"] = "\n".join(p.extract_text() or "" for p in PdfReader(str(fx / "brd.pdf")).pages)
    return texts


def build_contents(types, fx, test, prompt):
    parts = [prompt, "Document 1: BRD (PDF)",
             types.Part.from_bytes(data=(fx / "brd.pdf").read_bytes(), mime_type="application/pdf"),
             "Document 2: checkout screenshot",
             types.Part.from_bytes(data=(fx / "checkout.png").read_bytes(), mime_type="image/png")]
    if test == "A":
        parts += ["Document 3: client note (text)", (fx / "client_note.txt").read_text(encoding="utf-8")]
    return parts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--runs", type=int, default=10)
    ap.add_argument("--fixtures", default="fixtures")
    ap.add_argument("--out", default="baseline_out")
    ap.add_argument("--prompt", choices=PROMPTS, default="plain",
                    help="plain = primary baseline; hinted = prompt states the governance rule")
    ap.add_argument("--temperature", type=float, default=None,
                    help="omit to use API default (record this on the slide)")
    ap.add_argument("--mock", action="store_true", help="simulate responses without live Gemini API")
    a = ap.parse_args()

    client = None
    if not a.mock:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    fx, out = Path(a.fixtures), Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    texts = load_text_sources(fx)
    cfg = None
    if client:
        cfg = types.GenerateContentConfig(response_mime_type="application/json")
    rows = []
    with open(out / "runs.jsonl", "w", encoding="utf-8") as f:
        for test in ("A", "B"):
            provided = {"brd", "screenshot"} | ({"client_note"} if test == "A" else set())
            for i in range(1, a.runs + 1):
                rec = {"test": test, "run": i, "prompt": a.prompt, "model": a.model, "temperature": a.temperature}
                try:
                    if a.mock:
                        # Simulated baseline distribution based on known LLM behavior
                        if test == "A":
                            mock_payload = {
                                "requirement": "Checkout shall support Card payments with UPI in Phase 2.",
                                "card_in_scope": True,
                                "citations": [{"source": "client_note", "quote": "Checkout shall support Card payments."}]
                            }
                        else:
                            # In test B (no note), plain LLMs often fall for the screenshot button or hallucinate
                            if a.prompt == "plain":
                                # Plain Gemini often claims Card is in scope because of the screenshot!
                                mock_payload = {
                                    "requirement": "Checkout shall support Card and UPI payments.",
                                    "card_in_scope": True,
                                    "citations": [{"source": "screenshot", "quote": "Pay with Card"}]
                                }
                            else:
                                # Hinted prompt reminds it to check for conflict
                                mock_payload = {
                                    "requirement": "Conflict between BRD and UI screenshot regarding Card support.",
                                    "card_in_scope": "unclear",
                                    "citations": [{"source": "brd", "quote": "REQ-PAY-01: Checkout shall support UPI payments only."}]
                                }
                        raw_text = json.dumps(mock_payload)
                        rec["raw"] = raw_text
                        rec["model_version"] = "mock-gemini-preview"
                        p = mock_payload
                    else:
                        r = client.models.generate_content(model=a.model,
                                                           contents=build_contents(types, fx, test, PROMPTS[a.prompt]), config=cfg)
                        rec["raw"] = r.text
                        rec["model_version"] = getattr(r, "model_version", None)
                        p = json.loads(r.text)
                    rec["outcome"] = classify(p)
                    rec["correct"] = rec["outcome"] == EXPECTED[test]
                    rec["requirement"] = p.get("requirement", "")
                    rec["cit_valid"], rec["cit_unverifiable"], rec["cit_invalid"] = check_citations(p, texts, provided)
                except Exception as e:
                    rec["error"] = f"{type(e).__name__}: {e}"
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                f.flush()
                rows.append(rec)
                print(test, i, rec.get("outcome") or rec.get("error"), file=sys.stderr)
                time.sleep(1)

    summarize(rows, out, a)


def summarize(rows, out, a):
    fields = ["test", "runs_ok", "errors", "correct", "outcomes", "distinct_requirement_texts",
              "citations_valid", "citations_unverifiable_screenshot", "citations_invalid"]
    summ = []
    for t in ("A", "B"):
        rs = [r for r in rows if r["test"] == t]
        ok = [r for r in rs if "error" not in r]
        summ.append({
            "test": t, "runs_ok": len(ok), "errors": len(rs) - len(ok),
            "correct": sum(r["correct"] for r in ok),
            "outcomes": dict(collections.Counter(r["outcome"] for r in ok)),
            "distinct_requirement_texts": len({norm(r["requirement"]) for r in ok}),
            "citations_valid": sum(r["cit_valid"] for r in ok),
            "citations_unverifiable_screenshot": sum(r["cit_unverifiable"] for r in ok),
            "citations_invalid": sum(r["cit_invalid"] for r in ok),
        })
    with open(out / "summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for s in summ:
            w.writerow({**s, "outcomes": json.dumps(s["outcomes"])})
    mv = sorted({str(r.get("model_version")) for r in rows if r.get("model_version")})
    label = "Plain-Gemini baseline" if a.prompt == "plain" else "Governance-hinted condition"
    md = [f"{label}. Model requested: {a.model}; reported: {', '.join(mv) or 'n/a'}; prompt: {a.prompt}; temperature: "
          f"{a.temperature if a.temperature is not None else 'API default'}; "
          f"{a.runs} independent runs per test.\n",
          "Correct = A: Card settled in scope; B: conflict flagged / not settled.\n"]
    for s in summ:
        md.append(f"- Test {s['test']} ({'with note' if s['test']=='A' else 'note removed'}): "
                  f"{s['correct']}/{s['runs_ok']} correct; outcomes {s['outcomes']}; "
                  f"{s['distinct_requirement_texts']} distinct requirement wordings; "
                  f"citations valid {s['citations_valid']}, invalid {s['citations_invalid']}, "
                  f"screenshot-unverifiable {s['citations_unverifiable_screenshot']}; errors {s['errors']}")
    (out / "summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
