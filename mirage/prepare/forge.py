"""forge: build the fake twin of a crown jewel (same format, same shape, invented values, beacons).

Structured files (CSV, .env) are forged by code: a CSV needs thousands of consistent cells and a
7B model is slow and sloppy at that. Free text (memos, contracts) can be rewritten by an LLM when
MIRAGE_LLM is set; the LLM answer is only accepted if it passes verify_decoy, otherwise the
deterministic text forger is used. Careful: with MIRAGE_LLM=anthropic the real text leaves the
machine. Use a local model (ollama) for real data. In this hackathon the data is synthetic.

Beacons follow the team format: lmn_canary_<hex> for keys, <name>.<hex>@lumen-canary.test for
emails. They never imitate a real secret format, so secret scanners do not flag the repo.
"""
from __future__ import annotations

import csv
import io
import random
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from . import llm
from .pools import DIAGNOSES, DOMAINS, FIRST, LAST

API_URL = "http://internal-api.lumen.local"
CANARY_DOMAIN = "lumen-canary.test"


class UnsupportedFile(Exception):
    """No twin can be built (binary or undecodable content)."""


@dataclass
class TwinContext:
    rng: random.Random
    api_url: str = API_URL
    canary_rows: int = 3  # how many CSV rows get a canary email
    beacons: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def hex(self, n: int) -> str:
        return "".join(self.rng.choice("0123456789abcdef") for _ in range(n))


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def shape_scramble(value: str, rng: random.Random) -> str:
    """Replace each character by a random one of the same class (digit / lower / upper)."""
    out = []
    for ch in value:
        if ch.isdigit():
            out.append(rng.choice("0123456789"))
        elif ch.islower():
            out.append(rng.choice("abcdefghijklmnopqrstuvwxyz"))
        elif ch.isupper():
            out.append(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        else:
            out.append(ch)
    return "".join(out)


_SYL_C = "bcdfghjklmnprstvz"
_SYL_V = "aeiou"


def invented_word(rng: random.Random, avoid: set) -> str:
    w = ""
    for _ in range(100):
        w = "".join(rng.choice(_SYL_C) + rng.choice(_SYL_V) for _ in range(rng.choice((2, 3)))).capitalize()
        if w not in avoid:
            return w
    return w + "x"


def _unique(gen, avoid: set, used: set) -> str:
    for _ in range(200):
        v = gen()
        if v not in avoid and v not in used:
            used.add(v)
            return v
    v = gen() + str(len(used))
    used.add(v)
    return v


# --------------------------------------------------------------------------------------
# CSV
# --------------------------------------------------------------------------------------
_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_FR = re.compile(r"^\d{2}/\d{2}/\d{4}$")


def column_kind(header: str) -> str:
    h = header.lower()
    if re.search(r"social|ssn|nir|security", h):
        return "ssn"
    if "iban" in h:
        return "iban"
    if "mail" in h:
        return "email"
    if re.search(r"phone|tel|mobile", h):
        return "phone"
    if "first" in h:
        return "first"
    if re.search(r"last|surname", h):
        return "last"
    if "name" in h:
        return "name"
    if re.search(r"date|dob|birth", h):
        return "date"
    if re.search(r"amount|price|total|salary|cost|eur", h):
        return "amount"
    if re.search(r"(^|_)id$|_id|ref|number|code", h):
        return "id"
    return "other"


IDENTITY_KINDS = {"ssn", "iban", "email", "phone", "name", "id"}


def _parse_date(v: str):
    try:
        if _DATE_ISO.match(v):
            return date.fromisoformat(v), "iso"
        if _DATE_FR.match(v):
            d, m, y = v.split("/")
            return date(int(y), int(m), int(d)), "fr"
    except ValueError:
        pass
    return None, None


def _fmt_date(d: date, fmt: str) -> str:
    return d.isoformat() if fmt == "iso" else d.strftime("%d/%m/%Y")


def csv_twin(data: bytes, ctx: TwinContext) -> bytes:
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"))))
    if not rows:
        raise UnsupportedFile("empty csv")
    header, body = rows[0], rows[1:]
    ncols = len(header)
    cols = [[r[i] if i < len(r) else "" for r in body] for i in range(ncols)]
    kinds = [column_kind(h) for h in header]
    rng = ctx.rng
    avoid = [set(c) for c in cols]
    used = [set() for _ in range(ncols)]

    cats = []
    for i, c in enumerate(cols):
        distinct = sorted(set(c))
        is_cat = kinds[i] == "other" and 0 < len(distinct) <= max(12, len(c) // 10)
        cats.append(distinct if is_cat else None)

    def id_pattern(values):
        for v in values:
            m = re.match(r"^(\D*)(\d+)(\D*)$", v)
            if m:
                return m.group(1), len(m.group(2)), m.group(3)
        return None

    id_pat = [id_pattern(c) if kinds[i] == "id" else None for i, c in enumerate(cols)]

    # Real ids often grow with the row number. A fake id column that jumps around is an obvious tell,
    # so for such columns we draw sorted random numbers inside the real range, none of them real.
    mono_ids = {}
    for i, pat in enumerate(id_pat):
        if not pat:
            continue
        nums = [int(re.sub(r"\D", "", v)) for v in cols[i] if re.search(r"\d", v)]
        if len(nums) > 2 and sum(b > a for a, b in zip(nums, nums[1:])) >= 0.9 * (len(nums) - 1):
            real = set(nums)
            lo, hi = min(nums), max(nums)
            pool = [x for x in rng.sample(range(lo, hi + 1), min(hi - lo + 1, len(nums) * 3)) if x not in real]
            if len(pool) >= len(nums):
                mono_ids[i] = iter(sorted(pool[:len(nums)]))
    date_info, amount_info = [], []
    for i, c in enumerate(cols):
        ds = [(d, f) for d, f in (_parse_date(v) for v in c) if d]
        date_info.append((min(d for d, _ in ds), max(d for d, _ in ds), ds[0][1]) if ds else None)
        try:
            nums = [float(v) for v in c if v != ""]
            dec = len(c[0].split(".")[1]) if c and "." in c[0] else 0
            amount_info.append((min(nums), max(nums), dec) if nums and kinds[i] == "amount" else None)
        except ValueError:
            amount_info.append(None)
    email_domains = {i: sorted({v.split("@")[-1] for v in c if "@" in v}) for i, c in enumerate(cols)}

    name_cols = [i for i, k in enumerate(kinds) if k == "name"]
    avoid_names = set().union(*(avoid[i] for i in name_cols)) if name_cols else set()
    used_names: set = set()
    new_rows = []
    for _ in body:
        if name_cols:  # one invented person per row, reused by name, first, last and email columns
            first, last = _unique(lambda: f"{rng.choice(FIRST)} {rng.choice(LAST)}", avoid_names, used_names).split(" ", 1)
        else:
            first, last = rng.choice(FIRST), rng.choice(LAST)
        row = []
        for i in range(ncols):
            k = kinds[i]
            if k == "first":
                v = first
            elif k == "last":
                v = last
            elif k == "name":
                v = f"{first} {last}"
            elif k == "email":
                doms = email_domains[i] or DOMAINS
                v = _unique(lambda: f"{first.lower()}.{last.lower()}{rng.randint(1, 99)}@{rng.choice(doms)}",
                            avoid[i], used[i])
            elif k in ("phone", "ssn", "iban"):
                sample = next((s for s in cols[i] if s), "0000000000")
                keep = 2 if k == "iban" else (4 if k == "phone" else 1)
                v = _unique(lambda: sample[:keep] + shape_scramble(sample[keep:], rng), avoid[i], used[i])
            elif k == "id" and i in mono_ids:
                pre, n, post = id_pat[i]
                v = f"{pre}{next(mono_ids[i]):0{n}d}{post}"
            elif k == "id" and id_pat[i]:
                pre, n, post = id_pat[i]
                v = _unique(lambda: pre + "".join(rng.choice("0123456789") for _ in range(n)) + post,
                            avoid[i], used[i])
            elif k == "date" and date_info[i]:
                lo, hi, fmt = date_info[i]
                v = _fmt_date(lo + timedelta(days=rng.randint(0, max((hi - lo).days, 0))), fmt)
            elif k == "amount" and amount_info[i]:
                lo, hi, dec = amount_info[i]
                v = f"{rng.uniform(lo, hi):.{dec}f}"
            elif cats[i]:
                v = rng.choice(cats[i])
            elif header[i].lower() == "diagnosis":
                v = rng.choice(DIAGNOSES)
            else:
                sample = rng.choice(cols[i]) if cols[i] else ""
                v = shape_scramble(sample, rng)
                if k in IDENTITY_KINDS:
                    v = _unique(lambda: shape_scramble(sample, rng), avoid[i], used[i])
            row.append(v)
        new_rows.append(row)

    # Canary emails: a few rows get an address on our canary domain. If one is ever mailed, we know.
    email_cols = [i for i, k in enumerate(kinds) if k == "email"]
    if email_cols and new_rows and ctx.canary_rows:
        ec = email_cols[0]
        for r in rng.sample(range(len(new_rows)), min(ctx.canary_rows, len(new_rows))):
            addr = f"{rng.choice(FIRST)[0].lower()}.{rng.choice(LAST).lower()}.{ctx.hex(4)}@{CANARY_DOMAIN}"
            new_rows[r][ec] = addr
            ctx.beacons.append(addr)

    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(header)
    w.writerows(new_rows)
    return out.getvalue().encode("utf-8")


# --------------------------------------------------------------------------------------
# .env style files
# --------------------------------------------------------------------------------------
ENV_LINE = re.compile(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)(\s*=\s*)(.*)$")
SECRET_KEY = re.compile(r"KEY|TOKEN|SECRET|PASS|PWD", re.I)
API_KEY_NAME = re.compile(r"API_?KEY|API_?TOKEN|ACCESS_?KEY", re.I)
URL_KEY = re.compile(r"API_(BASE_)?URL|ENDPOINT", re.I)


def _random_like(real: str, rng: random.Random) -> str:
    if re.fullmatch(r"[0-9a-f]+", real):
        alphabet = "0123456789abcdef"
    elif re.fullmatch(r"[0-9]+", real):
        alphabet = "0123456789"
    elif re.fullmatch(r"[a-z0-9]+", real):
        alphabet = "abcdefghjkmnpqrstuvwxyz23456789"
    else:
        alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(rng.choice(alphabet) for _ in range(len(real)))


def env_twin(data: bytes, ctx: TwinContext) -> bytes:
    rng = ctx.rng
    out = []
    for line in data.decode("utf-8").splitlines():
        m = ENV_LINE.match(line)
        if not m or line.lstrip().startswith("#"):
            out.append(line)
            continue
        lead, key, eq, raw = m.groups()
        quote = raw[0] if raw[:1] in "\"'" and raw[-1:] == raw[:1] and len(raw) > 1 else ""
        val = raw[1:-1] if quote else raw
        if URL_KEY.search(key) and val.startswith("http"):
            new = ctx.api_url  # the tripwire: whoever uses the stolen key talks to our honey API
        elif API_KEY_NAME.search(key):
            new = f"lmn_canary_{ctx.hex(10)}"
            ctx.beacons.append(new)
        elif "://" in val:
            m2 = re.match(r"^([a-z0-9+.-]+)://(?:([^:@/]*)(?::([^@/]*))?@)?([^:/]+)(.*)$", val, re.I)
            if m2:
                scheme, user, pw, _host, rest = m2.groups()
                cred = f"{shape_scramble(user, rng)}:{_random_like(pw or 'x' * 16, rng)}@" if user is not None else ""
                new = f"{scheme}://{cred}{invented_word(rng, set()).lower()}.internal.example{rest}"
            else:
                new = shape_scramble(val, rng)
        elif SECRET_KEY.search(key):
            new = _random_like(val, rng)
        elif re.fullmatch(r"[A-Za-z]{1,12}", val) or val == "":
            new = val  # APP_ENV=production style: not sensitive
        else:
            new = shape_scramble(val, rng)
        out.append(f"{lead}{key}{eq}{quote}{new}{quote}")
    return ("\n".join(out) + "\n").encode("utf-8")


# --------------------------------------------------------------------------------------
# free text (contracts, memos)
# --------------------------------------------------------------------------------------
COMMON = {w.lower() for w in """
this that these those with from into over under between among about after before during while
agreement agreements supply contract contracts services service party parties scope price payment
payments payable instalments instalment confidentiality confidential contact term terms years year
both shall will have been which such other each upon where whereas whereof hereby memo memorandum
clauses clause article articles section sections notice notices liability termination governing law
purchase order invoice invoices delivery equipment imaging clinic clinics health medical devices
device systems system holiday policy employees employee leave days paid requests request portal
weeks ahead newsletter autumn flu shots available october november december january february
march april june july august september monday tuesday wednesday thursday friday saturday sunday
gmbh sas sarl ltd inc llc plc eur usd total made represented reached email phone iban note notes
please thank thanks hello dear regards best summary draft final internal subject date from
""".split()}

TEXT_TOKEN = re.compile(
    r"(?P<email>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)"
    r"|(?P<iban>\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,3})?\b)"
    r"|(?P<phone>\+\d{2}(?: ?\d){7,12})"
    r"|(?P<date>\b\d{4}-\d{2}-\d{2}\b)"
    r"|(?P<num>\b\d{5,}(?:\.\d+)?\b)"
    r"|(?P<cap>\b[A-Z][A-Za-z]{3,}\b)"
)


def text_twin(data: bytes, ctx: TwinContext) -> bytes:
    rng = ctx.rng
    text = data.decode("utf-8")
    real_caps = {m.group("cap") for m in TEXT_TOKEN.finditer(text) if m.group("cap")}
    mapping: dict = {}

    def repl(m: re.Match) -> str:
        kind, s = m.lastgroup, m.group(0)
        if s in mapping:
            return mapping[s]
        if kind == "email":
            new = f"{rng.choice(FIRST).lower()}.{invented_word(rng, set()).lower()}@{s.split('@')[1]}"
        elif kind == "iban":
            new = s[:2] + shape_scramble(s[2:], rng)
        elif kind == "phone":
            new = s[:3] + shape_scramble(s[3:], rng)
        elif kind == "date":
            new = (date.fromisoformat(s) + timedelta(days=rng.randint(-60, 60))).isoformat()
        elif kind == "num":
            new = str(rng.randint(1, 9)) + shape_scramble(s[1:], rng)
        else:
            if s.lower() in COMMON:
                return s
            new = invented_word(rng, real_caps)
            if s.isupper():
                new = new.upper()
        mapping[s] = new
        return new

    return TEXT_TOKEN.sub(repl, text).encode("utf-8")


_LLM_SYSTEM = (
    "You forge decoy documents for a defensive deception system. Rewrite the document so that every "
    "real name, company, place, amount, date, IBAN, email and phone number is replaced by a plausible "
    "invented one. Keep the structure, tone, length and formatting. Replace consistently (the same "
    "original value always becomes the same invented value). Output only the rewritten document."
)


def llm_text_twin(data: bytes, ctx: TwinContext):
    """Ask the LLM for a nicer twin. Returns bytes, or None if unavailable. Caller must verify."""
    if not llm.enabled():
        return None
    try:
        text = llm.complete("DOCUMENT:\n" + data.decode("utf-8"), _LLM_SYSTEM, max_tokens=4000)
    except llm.LLMUnavailable as e:
        ctx.notes.append(f"llm twin unavailable: {e}")
        return None
    return text.strip().encode("utf-8") + b"\n" if text.strip() else None


# --------------------------------------------------------------------------------------
# public API
# --------------------------------------------------------------------------------------
def detect_kind(name: str) -> str:
    low = name.lower()
    if low.endswith(".csv"):
        return "csv"
    if low == ".env" or low.endswith(".env") or low.startswith(".env."):
        return "env"
    return "text"


def make_twin(name: str, data: bytes, ctx: TwinContext, use_llm: bool = False, verify=None) -> bytes:
    """Build a twin. `verify(name, real, fake) -> list_of_problems` gates any LLM output."""
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as e:
        raise UnsupportedFile(f"{name}: not UTF-8 text") from e
    kind = detect_kind(name)
    if kind == "csv":
        return csv_twin(data, ctx)
    if kind == "env":
        return env_twin(data, ctx)
    if use_llm and verify is not None:
        candidate = llm_text_twin(data, ctx)
        if candidate is not None:
            problems = verify(name, data, candidate)
            if not problems:
                ctx.notes.append("text twin written by LLM")
                return candidate
            ctx.notes.append(f"LLM twin rejected ({len(problems)} problems), used code forger")
    return text_twin(data, ctx)
