"""中文字段名归一与相似度。"""
import re

from .glossary import SYNONYM_GROUPS

_UNIT = re.compile(r"[（(][^）)]*[)）]")
_SPACE = re.compile(r"\s+")


def _build_synonym_regex():
    canon = {}
    for group in SYNONYM_GROUPS:
        if len(group[0]) == 1:      # 单字组只做后缀归一，见 normalize
            continue
        for w in group:
            canon.setdefault(w, group[0])
    words = sorted(canon, key=len, reverse=True)
    return re.compile("|".join(map(re.escape, words))), canon


_SYN_RE, _SYN = _build_synonym_regex()


def strip(label):
    return _SPACE.sub("", _UNIT.sub("", label or "")).strip()


def normalize(label, synonyms=True):
    s = strip(label)
    if not synonyms or not s:
        return s
    s = _SYN_RE.sub(lambda m: _SYN[m.group(0)], s)
    if s.endswith("量") and len(s) > 2 and not s.endswith("电量"):
        s = s[:-1] + "数"
    if s.endswith("率") and len(s) > 1:
        s = s[:-1] + "占比"
    return s


def _bigrams(s):
    return {s[i:i + 2] for i in range(len(s) - 1)} or {s}


def similarity(a, b, synonyms=True):
    """0~1。完全相同=1；包含关系按长度比例；否则二元组 Dice。"""
    x, y = normalize(a, synonyms), normalize(b, synonyms)
    if not x or not y:
        return 0.0
    if x == y:
        return 1.0
    short, long_ = sorted((x, y), key=len)
    if _is_subsequence(short, long_):
        # “工单数”⊂“工单总数”、“投诉数”⊂“投诉工单数”；首字相同说明修饰的是同一主体，加分
        return 0.5 + 0.4 * len(short) / len(long_) + (0.05 if short[0] == long_[0] else 0)
    bx, by = _bigrams(x), _bigrams(y)
    return 0.9 * 2 * len(bx & by) / (len(bx) + len(by))


def _is_subsequence(short, long_):
    it = iter(long_)
    return all(ch in it for ch in short)


def best_similarity(label, names, synonyms=True):
    best, hit = 0.0, ""
    for n in names:
        s = similarity(label, n, synonyms)
        if s > best:
            best, hit = s, n
    return best, hit


def camel(col):
    parts = [p for p in col.lower().split("_") if p]
    return parts[0] + "".join(p.capitalize() for p in parts[1:]) if parts else col
