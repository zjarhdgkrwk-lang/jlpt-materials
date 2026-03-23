#!/usr/bin/env python3
"""
JLPT materials style audit script.
Detects A1~A6 violations. Read-only — no file modifications.
"""
import re
import csv
from pathlib import Path
from collections import Counter

BASE = Path("/home/user/jlpt-materials")

FILES = [
    "N5/N5_상편_Ch1-6_v2-1.md",
    "N5/N5_하편_Ch7-12.md",
    "N4/N4_상편_Ch1-8.md",
    "N4/N4_하편_Ch9-15.md",
    "N3/N3_상편_Ch1-8.md",
    "N3/N3_하편_Ch9-14.md",
    "N2/N2_상편_Ch1-7.md",
    "N2/N2_하편_Ch8-13.md",
    "N1/N1_상편_Ch1-5.md",
    "N1/N1_중편_Ch6-10.md",
    "N1/N1_하편_Ch11-15.md",
]

findings = []  # (code, filepath, lineno, content)


def add(code, fpath, lno, line):
    findings.append((code, fpath, lno, line.strip()[:50]))


# ── compiled patterns ──────────────────────────────────────────────────────────
HIRAGANA_ONLY   = re.compile(r'^[\u3041-\u3096\u309D\u309E]+$')
KATAKANA_ONLY   = re.compile(r'^[\u30A0-\u30FF]+$')
KOREAN          = re.compile(r'[가-힣]')
JP_CHAR         = re.compile(r'[\u3041-\u3096\u30A0-\u30FF\u4E00-\u9FFF]')
JP_CONSEC5      = re.compile(r'[\u3041-\u3096\u30A0-\u30FF]{5,}')

RUBY_RE         = re.compile(r'<ruby>(.*?)<rt>(.*?)</rt></ruby>')
EMPTY_RT        = re.compile(r'<rt>\s*</rt>')

# A2
A2_RE           = re.compile(r'の비교\s*참조')

# A3: Korean char or ) immediately followed by a Japanese particle
A3_PARTICLE     = re.compile(r'[가-힣\u3131-\u318E)]([のとはがを])')

# A4
A4_START        = re.compile(r'^[\[［]장면')

# A5
NUMBERED_EX     = re.compile(r'^[１２３４５６７８９０1-9][.．]')

# A6
A6_TERMS        = re.compile(
    r'\b(nai[-\s]stem|plain\s+form|te[-\s]form|nai\s+form|stem)\b',
    re.IGNORECASE
)

HEADER_RE       = re.compile(r'^#{1,6}\s')
HR_RE           = re.compile(r'^-{3,}$')

# ── helpers ────────────────────────────────────────────────────────────────────
def strip_tags(text):
    return re.sub(r'<[^>]+>', '', text)

def strip_quoted(text):
    """Remove 「…」 and `…` spans (inline quoted expressions)."""
    text = re.sub(r'「[^」]*」', '', text)
    text = re.sub(r'`[^`]*`', '', text)
    return text

def strip_rt(text):
    """Remove ruby reading content."""
    return re.sub(r'<rt>[^<]*</rt>', '', text)

# ── check functions ────────────────────────────────────────────────────────────

def chk_a1(line, fp, lno):
    # 빈 rt 태그
    if EMPTY_RT.search(line):
        add('A1', fp, lno, line)
        return
    for m in RUBY_RE.finditer(line):
        base = strip_tags(m.group(1)).strip()
        if not base:
            continue
        # 한글 base
        if KOREAN.search(base):
            add('A1', fp, lno, line)
            return
        # 히라가나만
        if HIRAGANA_ONLY.match(base):
            add('A1', fp, lno, line)
            return
        # 가타카나만
        if KATAKANA_ONLY.match(base):
            add('A1', fp, lno, line)
            return


def chk_a2(line, fp, lno):
    if A2_RE.search(line):
        add('A2', fp, lno, line)


def chk_a3(line, fp, lno):
    clean = strip_quoted(line)
    if A3_PARTICLE.search(clean):
        add('A3', fp, lno, line)


def chk_a4(line, fp, lno):
    if A4_START.match(line.strip()) and JP_CHAR.search(line):
        add('A4', fp, lno, line)


def chk_a5(line, fp, lno):
    s = line.strip()
    if not s:                       return
    if s.startswith('|'):           return   # 표 행
    if s.startswith('```'):         return
    if s.startswith('#'):           return   # 헤더
    if NUMBERED_EX.match(s):        return   # 예문 번호
    if not KOREAN.search(line):     return   # 한글 없음

    # 「」·백틱 제거 → rt 제거 → html 태그 제거
    clean = strip_quoted(line)
    clean = strip_rt(clean)
    clean = strip_tags(clean)

    if JP_CONSEC5.search(clean):
        add('A5', fp, lno, line)


def chk_a6(line, fp, lno):
    if A6_TERMS.search(line):
        add('A6', fp, lno, line)


# ── main loop ─────────────────────────────────────────────────────────────────
for rel in FILES:
    fp = BASE / rel
    if not fp.exists():
        print(f"[SKIP] {rel} — 파일 없음")
        continue

    lines = fp.read_text(encoding='utf-8').splitlines()
    in_code      = False
    in_checklist = False

    for lno, line in enumerate(lines, 1):
        stripped = line.strip()

        # 코드블록 추적
        if stripped.startswith('```'):
            in_code = not in_code
            continue
        if in_code:
            continue

        # 체크리스트 섹션 추적
        if '✅ 확인 체크리스트' in line:
            in_checklist = True
        elif in_checklist and (HEADER_RE.match(line) or HR_RE.match(stripped)):
            in_checklist = False

        # 검사 실행
        chk_a1(line, rel, lno)
        chk_a2(line, rel, lno)
        if in_checklist:
            chk_a3(line, rel, lno)
        chk_a4(line, rel, lno)
        chk_a5(line, rel, lno)
        chk_a6(line, rel, lno)

# ── CSV 저장 ──────────────────────────────────────────────────────────────────
out = BASE / 'audit_report.csv'
with open(out, 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.writer(f)
    w.writerow(['항목코드', '파일명', '줄번호', '해당 줄 내용'])
    for row in findings:
        w.writerow(row)

# ── 콘솔 출력 ─────────────────────────────────────────────────────────────────
counter = Counter(r[0] for r in findings)
total   = len(findings)

print(f"\n{'='*65}")
print(f"  JLPT 스타일 감사 결과  —  총 {total}건")
print(f"{'='*65}")
print(f"{'코드':<6}  {'건수':>5}  설명")
print(f"{'-'*65}")
LABELS = {
    'A1': 'ruby 태그 오류',
    'A2': '비교 참조 の→의 미교정',
    'A3': '체크리스트 내 일본어 조사 혼재',
    'A4': '장면 설명 일본어',
    'A5': '한국어 설명 내 일본어 문장 삽입',
    'A6': '영어 문법 용어',
}
for code in ['A1','A2','A3','A4','A5','A6']:
    n = counter.get(code, 0)
    print(f"  {code}   {n:>5}건  {LABELS[code]}")
print(f"{'='*65}")

# 코드별 상세 출력
for code in ['A1','A2','A3','A4','A5','A6']:
    rows = [r for r in findings if r[0] == code]
    if not rows:
        continue
    print(f"\n── {code}: {LABELS[code]} ({len(rows)}건) ──")
    for _, fp, lno, content in rows:
        print(f"  {fp}:{lno:<6}  {content}")

print(f"\naudit_report.csv → {out}\n")
