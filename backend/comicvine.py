'''
Thin client around the ComicVine API.

two lookup behaviors:
1) No issue number provided (e.g. raw OCR text, or just a rough title/query):
   runs a plain /search, fuzzy-ranks results, and returns the top N
   candidates for a confirmation picker UI. Lightweight search, just gets comicvine id, title, issue num.

2) Issue number known (structured output from an Ollama VL model):
   does the precise volume -> issue filter lookup and returns a single,
   fully detailed record (with credits/characters), or None.
'''


from __future__ import annotations

import os
import re
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Union

import requests
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

BASE_URL = 'https://comicvine.gamespot.com/api'
USER_AGENT = 'Longbox/0.1 (comic cataloging app; personal project)'

# Fields we actually want back from ComicVine for the precise lookup.
# Notably includes person_credits/character_credits, which /search omits.
ISSUE_FIELD_LIST = ','.join([
    'id',
    'name',
    'issue_number',
    'cover_date',
    'store_date',
    'description',
    'deck',
    'image',
    'volume',
    'person_credits',
    'character_credits',
    'resource_type',
    'api_detail_url',
    'site_detail_url',
])


@dataclass
class Creator:
    name: str
    role: str  # ComicVine returns this as a comma-separated string, e.g. 'writer, penciler'


@dataclass
class Character:
    name: str


@dataclass
class ComicIssueRecord:
    '''Normalized representation of a single ComicVine issue, ready to hand to your DB layer.'''

    comicvine_id: int
    name: Optional[str]
    issue_number: Optional[str]
    volume_id: Optional[int]
    volume_name: Optional[str]
    cover_date: Optional[str]
    store_date: Optional[str]
    description: Optional[str]
    resource_type: Optional[str]
    cover_url: Optional[str]                  # full-res remote URL (super_url)
    thumb_url: Optional[str]                  # small remote URL, handy for a picker UI
    cover_local_path: Optional[str] = None    # filled in after download_cover()
    creators: list[Creator] = field(default_factory=list)
    characters: list[Character] = field(default_factory=list)



class ComicVineClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        user_agent: str = USER_AGENT,
        min_request_interval: float = 1.0,
    ):
        self.api_key = api_key or os.environ.get('COMICVINE_API_KEY')
        if not self.api_key:
            raise ValueError('COMICVINE_API_KEY not set and no api_key provided')

        self.session = requests.Session()
        self.session.headers.update({'User-Agent': user_agent})
        self.min_request_interval = min_request_interval
        self._last_request_time = 0.0

    # ---- low-level request handling ----------------------------------------

    def _throttle(self):
        '''ComicVine's free tier is easy to hammer by accident during a batch
        import — a small sleep keeps you from getting rate-limited mid-run.'''

        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)

    def _get(self, endpoint: str, params: dict) -> dict:
        self._throttle()
        params = {**params, 'api_key': self.api_key, 'format': 'json'}
        url = f'{BASE_URL}/{endpoint.lstrip('/')}'
        response = self.session.get(url, params=params, timeout=10)
        self._last_request_time = time.monotonic()
        response.raise_for_status()
        data = response.json()

        # ComicVine returns HTTP 200 even on API-level errors — status_code 1 means OK.
        if data.get('status_code') != 1:
            logger.warning('ComicVine API error: %s', data.get('error'))
        return data

    @staticmethod
    def _normalized_tokens(value: Optional[str]) -> list[str]:
        if not value:
            return []
        text = re.sub(r'[^a-z0-9]+', ' ', value.lower())
        return [token for token in text.split() if token and token not in {'the', 'of', 'and', 'a', 'an', 'issue'}]

    @classmethod
    def _token_overlap_score(cls, left: str, right: str) -> float:
        left_tokens = set(cls._normalized_tokens(left))
        right_tokens = set(cls._normalized_tokens(right))
        if not left_tokens or not right_tokens:
            return 0.0
        overlap = len(left_tokens & right_tokens)
        return (overlap / len(right_tokens)) * 100.0

    @classmethod
    def _candidate_similarity_score(cls, query: str, candidate: dict) -> float:
        ''' Rank issue results by the actual query structure instead of API ordering.
        Exact token overlap on volume name and creator names is weighted more
        heavily than a raw fuzzy phrase ratio because ComicVine search results are
        not sorted by relevance. '''


        if not query:
            return 0.0

        query_tokens = cls._normalized_tokens(query)
        if not query_tokens:
            return 0.0

        volume_name = (candidate.get('volume') or {}).get('name') or ''
        issue_name = candidate.get('name') or ''
        issue_number = str(candidate.get('issue_number') or '')
        creator_names = [
            person.get('name', '')
            for person in (candidate.get('person_credits') or [])
        ]

        volume_score = max(
            fuzz.token_set_ratio(query, volume_name),
            cls._token_overlap_score(query, volume_name),
        )
        issue_name_score = max(
            fuzz.token_set_ratio(query, issue_name),
            cls._token_overlap_score(query, issue_name),
        )

        issue_number_score = 0.0
        if issue_number:
            issue_number_tokens = cls._normalized_tokens(issue_number)
            if issue_number_tokens and any(token in query_tokens for token in issue_number_tokens):
                issue_number_score = 100.0
            else:
                issue_number_score = fuzz.token_set_ratio(query, issue_number)

        creator_score = 0.0
        if creator_names:
            creator_score = max(
                max(
                    fuzz.token_set_ratio(query, name),
                    cls._token_overlap_score(query, name),
                )
                for name in creator_names
                if name
            )

        score = (
            volume_score * 0.55 +
            issue_number_score * 0.25 +
            creator_score * 0.15 +
            issue_name_score * 0.05
        )

        if volume_name and volume_name.lower() in query.lower():
            score += 5.0
        if issue_number and issue_number in query.lower():
            score += 10.0

        return min(score, 100.0)

    # ---- volume lookup --------------------------------------------------------

    def best_volume_matches(self, query: str, limit: int = 20, top_n: int = 5) -> list[dict]:
        '''fuzzy-rank candidate volumes and return up to top_n.'''

        data = self._get('search', {'query': query, 'resources': 'volume', 'limit': limit})
        candidates = data.get('results', [])

        if not candidates:
            return []
        ranked = sorted(
            candidates,
            key=lambda c: fuzz.token_set_ratio(query, c.get('name', '')),
            reverse=True,
        )
        return ranked[:top_n]

    # ---- precise issue lookup -----------------------------

    def get_issue_by_volume(self, volume_id: int, issue_number: str) -> Optional[dict]:
        '''Filters directly on volume + issue_number instead of ranking /search
        hits, and requests field_list so creators/characters come back.'''

        params = {
            'filter': f'volume:{volume_id},issue_number:{issue_number}',
            'field_list': ISSUE_FIELD_LIST,
        }
        data = self._get('issues', params)
        results = data.get('results', [])
        return results[0] if results else None

    # ---- fuzzy search ----------------------------------
    def _search_candidates(self, query: str, top_n: int = 5, limit: int = 10) -> list[ComicIssueRecord]:
        '''/search api call, fuzzy-ranked, top N returned as lightweight candidates. volume/title match first, issue number second,
        creator names third. '''
        
        data = self._get('search', {'query': query, 'resources': 'issue', 'limit': limit})
        candidates = data.get('results', [])
        if not candidates:
            return []

        ranked = sorted(
            candidates,
            key=lambda c: self._candidate_similarity_score(query, c),
            reverse=True,
        )
        return [self._normalize_issue(c) for c in ranked[:top_n]]

    # ---- orchestration ----------------------------------------------------------

    def fetch_issue(
        self,
        text_query: Optional[str] = None,
        *,
        title: Optional[str] = None,
        issue: Optional[str] = None,
        creator: Optional[str] = None,
    ) -> Union[ComicIssueRecord, list[ComicIssueRecord], None]:
        '''If no issue num, run fuzzy search api call.
           If there is an issue num, run the exact /issue api call.'''
        
        if issue is None:
            query = text_query if text_query is not None else title
            if not query:
                raise ValueError('Provide text_query or title when issue is not known')
            if creator:
                query = f'{query} {creator}'
            return self._search_candidates(query, top_n=3)

        if not title:
            raise ValueError('title is required when issue is provided')

        volume_candidates = self.best_volume_matches(title, top_n=3)
        if not volume_candidates:
            logger.info('No volume match for %r', title)
            return None

        raw_issue = None
        matched_volume = None
        for volume in volume_candidates:
            raw_issue = self.get_issue_by_volume(volume['id'], issue)
            if raw_issue is not None:
                matched_volume = volume
                break

        if raw_issue is None:
            logger.info(
                "Checked %d volume candidate(s) for %r but issue #%s wasn't found in any of them",
                len(volume_candidates), title, issue,
            )
            return None

        logger.info(
            'Matched %r (id=%s) as the volume for issue #%s',
            matched_volume['name'], matched_volume['id'], issue,
        )
        record = self._normalize_issue(raw_issue)

        return record

    def hydrate(self, record: ComicIssueRecord) -> Optional[ComicIssueRecord]:
        '''call once user picks candidate from the top-3 list.
        given the candidates id, fetch the full record (credits + characters) via the precise volume+issue filter.'''

        if record.volume_id is None or record.issue_number is None:
            return None
        
        raw_issue = self.get_issue_by_volume(record.volume_id, record.issue_number)

        if raw_issue is None:
            return None
        
        return self._normalize_issue(raw_issue)

    # ---- normalization -------------------------------------------------------------

    @staticmethod
    def _strip_html(text: Optional[str]) -> Optional[str]:
        if not text:
            return text
        return re.sub(r'<[^>]+>', '', text).strip()

    def _normalize_issue(self, raw: dict) -> ComicIssueRecord:
        image = raw.get('image') or {}
        volume = raw.get('volume') or {}

        creators = [
            Creator(name=c.get('name', ''), role=c.get('role', ''))
            for c in raw.get('person_credits', []) or []
        ]
        characters = [
            Character(name=c.get('name', ''))
            for c in raw.get('character_credits', []) or []
        ]

        return ComicIssueRecord(
            comicvine_id=raw['id'],
            name=raw.get('name'),
            issue_number=raw.get('issue_number'),
            volume_id=volume.get('id'),
            volume_name=volume.get('name'),
            cover_date=raw.get('cover_date'),
            store_date=raw.get('store_date'),
            description=self._strip_html(raw.get('description') or raw.get('deck')),
            resource_type=raw.get('resource_type'),
            cover_url=image.get('super_url'),
            thumb_url=image.get('thumb_url'),
            creators=creators,
            characters=characters,
        )

    # ---- cover art download -----------------------------------------------------------

    def download_cover(self, record: ComicIssueRecord, dest_dir: str) -> Optional[str]:
        '''Download the full-res cover jpg and stash the local path on the record.'''
        if not record.cover_url:
            return None

        os.makedirs(dest_dir, exist_ok=True)
        filename = f'{record.comicvine_id}.jpg'
        dest_path = Path(dest_dir) / filename

        self._throttle()
        resp = self.session.get(record.cover_url, timeout=15)
        self._last_request_time = time.monotonic()
        resp.raise_for_status()
        dest_path.write_bytes(resp.content)

        record.cover_local_path = str(dest_path)
        return record.cover_local_path


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    client = ComicVineClient()

    # Scenario 1: no issue number known -> top 3 candidates for a picker
    candidates = client.fetch_issue('ABSOLUTE BATMAN 21 SCOTT SNYDER')
    for c in candidates:
        print(f'[candidate] {c.volume_name} #{c.issue_number} — {c.name}')

    # Scenario 2: structured fields from an Ollama VL model -> single record
    result = client.fetch_issue(title='Absolute Batman', issue='21', creator='Scott Snyder')
    if result:
        # print(result)
        print(f'[matched] {result.volume_name} #{result.issue_number} — {result.name}')

    # Scenario 3: the user chooses out of the 3 candidates, or manually edits an entry, and we collect the full issue
    updated_result = client.hydrate(record=candidates[0])
    print(updated_result)
    client.download_cover(record=updated_result, dest_dir='test_output')