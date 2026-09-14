import unittest

from backend.comicvine import ComicVineClient


class ComicVineRankingTests(unittest.TestCase):
    @staticmethod
    def _make_client(fake_results):
        client = ComicVineClient(api_key="test-key")
        client._get = lambda endpoint, params: {"results": fake_results}
        return client

    def test_candidate_score_prefers_exact_volume_and_issue_tokens(self):
        client = self._make_client([])

        candidate = {
            "id": 2,
            "name": "Absolute Batman #15",
            "issue_number": "15",
            "volume": {"id": 99, "name": "Absolute Batman"},
            "cover_date": "2024-01-01",
            "store_date": "2024-01-03",
            "description": "",
            "deck": "",
            "image": {"super_url": "", "thumb_url": ""},
            "resource_type": "issue",
            "person_credits": [{"name": "Scott Snyder", "role": "writer"}],
            "character_credits": [],
        }

        score = client._candidate_similarity_score(
            "absolute batman 15 scott snyder",
            candidate,
        )

        self.assertGreater(score, 90)

    def test_search_candidates_rank_best_match_first(self):
        fake_results = [
            {
                "id": 1,
                "name": "Batman #5",
                "issue_number": "5",
                "volume": {"id": 11, "name": "Batman"},
                "cover_date": "2023-12-01",
                "store_date": "2023-12-03",
                "description": "",
                "deck": "",
                "image": {"super_url": "", "thumb_url": ""},
                "resource_type": "issue",
                "person_credits": [],
                "character_credits": [],
            },
            {
                "id": 2,
                "name": "Absolute Batman #15",
                "issue_number": "15",
                "volume": {"id": 99, "name": "Absolute Batman"},
                "cover_date": "2024-01-01",
                "store_date": "2024-01-03",
                "description": "",
                "deck": "",
                "image": {"super_url": "", "thumb_url": ""},
                "resource_type": "issue",
                "person_credits": [{"name": "Scott Snyder", "role": "writer"}],
                "character_credits": [],
            },
        ]

        client = self._make_client(fake_results)
        ranked = client._search_candidates("absolute batman 15 scott snyder", top_n=2)

        self.assertEqual(ranked[0].comicvine_id, 2)
        self.assertEqual(ranked[0].volume_name, "Absolute Batman")


if __name__ == "__main__":
    unittest.main()
