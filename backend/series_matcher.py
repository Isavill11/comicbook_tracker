"""
Matches noisy OCR tokens from a comic cover against a known list of published
comic series titles. Works word-by-word rather than matching the whole
joined OCR string at once, since junk tokens (stray letters, indicia text
picked up by OCR) badly dilute a whole-string comparison.

SeriesMatcher owns the local reference data (a flat title list per
publisher, and a separate creator surname index) and exposes:
  - match_series()      word-by-word fuzzy title scoring
  - identify_creators()  surname-based signal from clean OCR tokens
  - resolve()             the three-band decision pipeline for /upload

"""

import json
import re
from typing import Dict, List, Tuple
from rapidfuzz import fuzz, process

_YEAR_RANGE_RE = re.compile(r'\s*\(\d.*?\)')
_STOPWORDS = {"the", "of", "in", "a", "an"}

DEFAULT_AUTO_ACCEPT_THRESHOLD = 90.0
DEFAULT_CONFIRM_THRESHOLD = 65.0
DEFAULT_CREATOR_SURNAME_THRESHOLD = 85
DEFAULT_TOP_N = 5


class SeriesMatcher:
    """
    Loads the local title/creator reference data once and reuses it across
    every match_series()/resolve() call — important since this will be
    called once per detected comic on every /upload request.
    """

    def __init__(
        self,
        series_json_path: str,
        creators_json_path: str,
        auto_accept_threshold: float = DEFAULT_AUTO_ACCEPT_THRESHOLD,
        confirm_threshold: float = DEFAULT_CONFIRM_THRESHOLD,
        creator_surname_threshold: int = DEFAULT_CREATOR_SURNAME_THRESHOLD,
    ):
        self.series_list = self._load_series_list(series_json_path)
        self.surname_lookup = self._load_surname_lookup(creators_json_path)

        self.auto_accept_threshold = auto_accept_threshold
        self.confirm_threshold = confirm_threshold
        self.creator_surname_threshold = creator_surname_threshold

    # ---------- loading ----------

    @staticmethod
    def _load_series_list(json_path: str) -> List[Tuple[str, str]]:
        """
        Flattens every publisher's title list into (publisher, title) pairs.
        Generic over whatever top-level publisher keys exist in the file
        (currently "DC" populated, "Marvel" empty) so nothing here needs to
        change once Marvel scraping is filled in.
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        series_list = []
        for publisher, titles in data.items():
            for title in titles:
                series_list.append((publisher, title))
        return series_list

    @staticmethod
    def _load_surname_lookup(json_path: str) -> Dict[str, List[str]]:
        with open(json_path, 'r', encoding='utf-8') as f:
            all_creators = json.load(f)["all_creators"]

        lookup: Dict[str, List[str]] = {}
        for name in all_creators:
            surname = name.split()[-1].upper()
            lookup.setdefault(surname, []).append(name)
        return lookup

    # ---------- cleaning helpers ----------

    @staticmethod
    def _clean_title_words(series_name: str) -> List[str]:
        name = _YEAR_RANGE_RE.sub('', series_name).strip()
        return [w for w in name.split() if len(w) >= 3 and w.lower() not in _STOPWORDS]

    @staticmethod
    def _best_word_match_score(words: List[str], usable_tokens: List[str]) -> float:
        """Average of each word's single best match against the OCR tokens."""
        if not words:
            return 0.0
        word_scores = [
            max(fuzz.ratio(word.upper(), tok) for tok in usable_tokens)
            for word in words
        ]
        return sum(word_scores) / len(word_scores)

    # ---------- creator signal ----------

    def identify_creators(self, ocr_tokens: List[str]) -> set:
        """
        Fuzzy-matches clean OCR tokens against known creator surnames using
        fuzz.ratio (not token_set_ratio — surnames are single clean tokens,
        so a plain ratio at a high threshold is the right tool here).

        Returns the set of full creator names whose surname matched. This
        is independent of series data — see the module docstring for why.
        """
        surnames = list(self.surname_lookup.keys())
        found = set()
        for token in ocr_tokens:
            match, score, _ = process.extractOne(
                token.upper(), surnames, scorer=fuzz.ratio
            )
            if match and score >= self.creator_surname_threshold:
                found.update(self.surname_lookup[match])
        return found

    # ---------- title matching ----------

    def match_series(
        self,
        ocr_tokens: List[str],
        top_n: int = DEFAULT_TOP_N,
        min_token_len: int = 3,
    ) -> List[Tuple[str, str, float]]:
        """
        Scores every (publisher, title) pair against ocr_tokens.
        Returns the top_n matches as (publisher, title, score),
        sorted best-first. score is 0-100.
        """

        usable_tokens = [t.upper() for t in ocr_tokens if len(t) >= min_token_len]
        if not usable_tokens:
            return []

        scored = []
        for publisher, title in self.series_list:
            title_words = self._clean_title_words(title)
            if not title_words:
                continue
            score = self._best_word_match_score(title_words, usable_tokens)
            scored.append((publisher, title, score))

        scored.sort(key=lambda item: -item[2])
        return scored[:top_n]

    # ---------- three-band decision pipeline ----------

    def resolve(self, ocr_tokens: List[str], top_n: int = DEFAULT_TOP_N) -> dict:
        """
        Runs the full local matching pipeline for one comic's OCR tokens.
        This is what the /upload endpoint should call per detected comic.

        Always returns up to top_n candidates so the frontend can show a
        picker (plus a "none of these" manual-entry option) regardless of
        confidence — "band" just tells you how much to lean on the top one:

          {"band": "auto_accept", "candidates": [(publisher, title, score), ...]}
          {"band": "confirm",     "candidates": [...]}
          {"band": "new_series",  "candidates": [...], "creator_hint": {...} | None}
        """

        matches = self.match_series(ocr_tokens, top_n=top_n)
        top_score = matches[0][2] if matches else 0.0

        if top_score >= self.auto_accept_threshold:
            band = "auto_accept"
        elif top_score >= self.confirm_threshold:
            band = "confirm"
        else:
            band = "new_series"

        result = {"band": band, "candidates": matches}
        if band == "new_series":
            result["creator_hint"] = self.identify_creators(ocr_tokens) or None
        return result


if __name__ == '__main__':
    # quick manual test using your real comic_tester_2.jpeg OCR output
    matcher = SeriesMatcher(
        series_json_path='comics_db/all_comic_series.json',
        creators_json_path='comics_db/all_comic_creators.json',
    )

    test_cases = {
        "comic_0 (Absolute Superman)": ["ABSOLUTE", "SSLZEAA", "ALLIR", "Mp"],
        "comic_1 (Absolute Batman)":   ["ABSOLI", "TE", "Ll", "ALLIA", "delltdeaa", "bat"],
        "comic_2 (Superman)":          ["SIIPERMAN", "IN", "S", "Wiliausov", "cauppell"],
        "comic_3 (Batman)":            ["eonicsV", "H", "EATNN", "B", "PUScINcIA", "U", "hh", "KM", "ZCON", "I", "I"],
        "comic_4 (Batman)":            ["Mk", "bel", "eowc", "EATMN", "CApulto"],
        "comic_5 (Superman Superboy prime)": "SUPERBOYPRINE HME SLRISHERE B6438 GIPERMAN REIGNge SUPERBOVS WILLIAMSON MORA ALLIN SANCHEZ".split()
    }

    for label, tokens in test_cases.items():
        result = matcher.resolve(tokens)
        print(f"\n{label}: band={result['band']}")
        for publisher, title, score in result["candidates"]:
            print(f"    {title:35s} ({publisher})  score={score:.1f}")
        if result.get("creator_hint"):
            print(f"    creator hint: {result['creator_hint']}")