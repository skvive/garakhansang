"""Security and persistence smoke tests for merchant onboarding API."""
import json
import sqlite3
import unittest
from unittest.mock import patch

from admin_core import merchant_community as api

SCHEMA = """
CREATE TABLE merchant_applications (
id INTEGER PRIMARY KEY, author_id TEXT, shop_name TEXT, contact_name TEXT,
phone TEXT, email TEXT, category TEXT, shop_location TEXT, description TEXT,
consent_at TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
reviewed_at TEXT);
CREATE TABLE community_posts (
id INTEGER PRIMARY KEY, author_id TEXT, author_label TEXT, category TEXT,
title TEXT, body TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
reviewed_at TEXT);
CREATE TABLE community_comments (
id INTEGER PRIMARY KEY, post_id INTEGER, author_id TEXT, author_label TEXT,
body TEXT, status TEXT DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP,
reviewed_at TEXT);
"""


class CommunityTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)
        self.patches = [
            patch.object(api, "connect", return_value=self.db),
            patch.object(api, "use_postgres", return_value=True),
        ]
        for item in self.patches:
            item.start()
        self.addCleanup(self.close)

    def close(self):
        for p in reversed(self.patches):
            p.stop()
        self.db.close()

    def request(self, method, path, payload=None, authenticated=False):
        headers = {"host": "garakmall.lexid.site", "origin": "https://garakmall.lexid.site"}
        if payload is not None:
            headers["content-type"] = "application/json"
        body = json.dumps(payload or {}).encode() if payload is not None else b""
        if authenticated:
            headers["authorization"] = "Bearer "+"x"*40
            with patch.object(api, "member", return_value={"id": "user1", "name": "Tester"}):
                status, _, raw = api.handle(method, path, headers, body)
        else:
            status, _, raw = api.handle(method, path, headers, body)
        return status, json.loads(raw)

    def test_public_board_only_approved(self):
        with self.db:
            self.db.execute("INSERT INTO community_posts(author_id,author_label,category,title,body) VALUES('user1','테스터','story','미공개','PRIVATE')")
            self.db.execute("INSERT INTO community_posts(author_id,author_label,category,title,body,status) VALUES('user2','공개','season','게시','PUBLIC','approved')")
        status, result = self.request("GET", "/api/community/posts")
        self.assertEqual(status, 200)
        self.assertEqual(len(result["items"]), 1)
        self.assertEqual(result["items"][0]["title"], "게시")

    def test_no_anonymous_write_or_admin_view(self):
        status, _ = self.request("POST", "/api/community/posts",
                                 {"category": "story", "title": "Test title", "content": "Test content"})
        self.assertEqual(status, 401)
        status, _ = self.request("GET", "/api/merchant-applications")
        self.assertEqual(status, 401)
        status, _ = self.request("GET", "/api/community/moderation")
        self.assertIn(status, (401, 403))

    def test_application_is_private_and_pending(self):
        values = dict(shopName="수산 테스트", contactName="Test", phone="010-1234-5678",
                      email="test@example.com", category="수산 / 활어", location="1층",
                      description="테스트 매장 소개를 위한 내용입니다.", consent=True)
        status, data = self.request("POST", "/api/merchant-applications", values, True)
        self.assertEqual(status, 201)
        self.assertEqual(data["status"], "pending")
        status, result = self.request("GET", "/api/merchant-applications", authenticated=True)
        self.assertEqual(status, 200)
        self.assertEqual(len(result["items"]), 1)
        self.assertNotIn("phone", result["items"][0])
        self.assertNotIn("email", result["items"][0])

    def test_post_and_comment_require_approval(self):
        status, data = self.request("POST", "/api/community/posts",
                                    {"category": "story", "title": "Real title", "content": "Real story content"}, True)
        self.assertEqual(status, 201)
        post_id = data["id"]
        # Account real names must never become public author labels implicitly.
        author=self.db.execute("SELECT author_label FROM community_posts WHERE id=?", (post_id,)).fetchone()["author_label"]
        self.assertEqual(author,"Tester")  # mocked member identity in this test; API member() enforces anonymous label
        status, data = self.request("GET", "/api/community/posts")
        self.assertEqual(data["items"], [])
        status, data = self.request("POST", "/api/community/comments",
                                    {"postId": post_id, "content": "Comment sample"}, True)
        self.assertEqual(status, 404)
        with self.db:
            self.db.execute("UPDATE community_posts SET status='approved' WHERE id=?", (post_id,))
        status, data = self.request("POST", "/api/community/comments",
                                    {"postId": post_id, "content": "Comment sample"}, True)
        self.assertEqual(status, 201)
        status, data = self.request("GET", "/api/community/comments?postId="+str(post_id))
        self.assertEqual(data["items"], [])

    def test_bad_origin_rejected(self):
        with patch.object(api, "use_postgres", return_value=True):
            status, _, _ = api.handle("POST", "/api/community/posts",
                                      {"origin":"https://evil.example","host":"garakmall.lexid.site"}, b"{}")
        self.assertEqual(status, 403)


    def test_member_name_is_not_public_full_name(self):
        import os
        from types import SimpleNamespace
        stub=SimpleNamespace(get_signing_key_from_jwt=lambda _:SimpleNamespace(key="test"))
        with patch.dict(os.environ,{"NEON_AUTH_BASE_URL":"https://example.neonauth.neon.tech/auth"}):
            with patch.object(api,"jwks",return_value=stub):
                with patch("jwt.decode",return_value={"sub":"userid","name":"Real Name","iss":"https://example.neonauth.neon.tech","exp":9999999999}):
                    user=api.member({"authorization":"Bearer fake.jwt.token"})
        self.assertEqual(user["id"],"userid")
        self.assertEqual(user["name"],"회원")

if __name__ == "__main__":
    unittest.main()
