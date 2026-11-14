"""Downloads the open specialist literature and cuts it into passages: data/corpus.jsonl.

    python build_corpus.py

Sources (ids as in backend/SOURCES.md): FAO-56 (S13), the Fundulea field-trial papers (S2, S3, S4) and two
reviews on heat and crops (S10, S11), and FAO paper 66 on crop yield response to water (S16). All in English. The Romanian sources (S1, S5, S6) are not in the
corpus; their figures are in crops.json and reach the model as facts.

The passages are other people's text. They are used for training only: data/ and the Colab archive stay
out of git. Needs `pdftotext` (poppler or xpdf) on the PATH for the PDF sources.
"""
import html
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0"}
FAO56 = {  # file -> chapter title; the equation and weather-station chapters (2-4) and the annexes are left out
    "x0490e04": "Chapter 1, Introduction to evapotranspiration",
    "x0490e0a": "Chapter 5, Introduction to crop evapotranspiration",
    "x0490e0b": "Chapter 6, Single crop coefficient",
    "x0490e0c": "Chapter 7, Dual crop coefficient",
    "x0490e0e": "Chapter 8, ETc under soil water stress conditions",
    "x0490e0f": "Chapter 9, ETc for natural, non-typical and non-pristine vegetation",
    "x0490e0g": "Chapter 10, ETc under various management practices",
    "x0490e0h": "Chapter 11, ETc during non-growing periods",
}
PDFS = {
    "S2": "https://agronomyjournal.usamv.ro/pdf/2025/issue_2/Art76.pdf",
    "S3": "https://www.incda-fundulea.ro/rar/nr1314/13.10.pdf",
    "S4": "https://agronomyjournal.usamv.ro/pdf/2021/issue_1/Art67.pdf",
    "S10": "https://pagesperso.locean-ipsl.upmc.fr/escape/luo2011.climaticchange.pdf",
}
FAO66 = "https://www.fao.org/4/i2800e/i2800e.pdf"  # S16, about 450 pages
PMC = {"S11": "https://pmc.ncbi.nlm.nih.gov/articles/PMC7316970"}


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def html_paragraphs(raw: str):
    raw = re.sub(r"(?is)<(script|style|table|figure|nav|header|footer).*?</\1>", " ", raw)
    return [clean(html.unescape(re.sub(r"<[^>]+>", " ", p))) for p in re.findall(r"(?is)<p[^>]*>(.*?)</p>", raw)]


def pdf_text(data: bytes) -> str:
    with tempfile.TemporaryDirectory() as d:
        pdf, txt = Path(d) / "a.pdf", Path(d) / "a.txt"
        pdf.write_bytes(data)
        subprocess.run(["pdftotext", "-enc", "UTF-8", str(pdf), str(txt)], check=True, capture_output=True)  # reading order
        return txt.read_text(encoding="utf-8", errors="replace")


def pdf_paragraphs(data: bytes):
    text = pdf_text(data)
    text = re.split(r"\n\s*REFERENCES\s*\n|\n\s*References\s*\n", text)[0]
    text = re.sub(r"-\n(?=[a-z])", "", text)  # words split at a line end
    return [clean(p) for p in re.split(r"\n\s*\n", text)]


def good(p: str) -> bool:
    words = p.split()
    if len(words) < 25:
        return False
    years = len(re.findall(r"\b(?:19|20)\d\d\b", p))
    if years > len(words) / 25 or re.match(r"(?i)(lead|contributing) authors?\b", p):  # reference lists, author lists
        return False
    digits = sum(c.isdigit() for c in p) / len(p)
    letters = sum(c.isalpha() for c in p) / len(p)
    return digits < 0.12 and letters > 0.7 and not p.lower().startswith(("table ", "figure ", "fig. ", "box ", "equation "))


def chunks(paragraphs, low=90, high=220):
    """Joins neighbouring paragraphs into passages of about 90 to 220 words."""
    out, cur = [], []
    for p in filter(good, paragraphs):
        words = p.split()
        while len(words) > high:  # a very long paragraph is cut at a sentence end
            cut = " ".join(words[:high])
            end = max(cut.rfind(". "), cut.rfind("; "))
            head = cut[:end + 1] if end > len(cut) // 2 else cut
            out.append(head)
            words = " ".join(words)[len(head):].split()
        cur.append(" ".join(words))
        if sum(len(c.split()) for c in cur) >= low:
            out.append(" ".join(cur))
            cur = []
    if cur and sum(len(c.split()) for c in cur) >= 40:
        out.append(" ".join(cur))
    return out


def main():
    rows = []
    for name, title in FAO56.items():
        paras = html_paragraphs(get(f"https://www.fao.org/4/x0490e/{name}.htm").decode("latin-1"))
        rows += [{"source": "S13", "locator": title, "text": c} for c in chunks(paras)]
        print("S13", title, len(paras))
    for sid, url in PDFS.items():
        paras = pdf_paragraphs(get(url))
        rows += [{"source": sid, "locator": "article text", "text": c} for c in chunks(paras)]
        print(sid, len(paras))
    pages = pdf_text(get(FAO66)).split("\f")
    before = len(rows)
    for number, page in enumerate(pages, 1):
        if re.search(r"(?m)^\s*REFERENCES\s*$", page):
            continue
        page = re.sub(r"-\n(?=[a-z])", "", page)
        rows += [{"source": "S16", "locator": f"PDF page {number}", "text": c}
                 for c in chunks([clean(x) for x in re.split(r"\n\s*\n", page)])]
    print("S16", len(pages), "pages,", len(rows) - before, "passages")
    for sid, url in PMC.items():
        raw = get(url).decode("utf-8", errors="replace")
        raw = raw.split('id="ref-list')[0]
        rows += [{"source": sid, "locator": "article text", "text": c} for c in chunks(html_paragraphs(raw))]
        print(sid)
    for i, r in enumerate(rows):
        r["id"] = f"p{i:04d}"
    (HERE / "data").mkdir(exist_ok=True)
    with open(HERE / "data" / "corpus.jsonl", "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    by = {}
    for r in rows:
        by[r["source"]] = by.get(r["source"], 0) + 1
    print(f"{len(rows)} passages, {sum(len(r['text'].split()) for r in rows)} words", by)


if __name__ == "__main__":
    main()
