from __future__ import annotations

import unittest

from scripts.fetch_public_social_candidates import (
    TelegramPreviewParser,
    message_to_candidate,
)

SOURCE = {
    "source_id": "telegram-test",
    "name": "Test Community",
    "platform": "telegram",
    "mode": "public_preview",
    "url": "https://t.me/s/testcommunity",
    "area_hints": ["Bishan"],
    "topic_hints": ["art"],
}


class TelegramPreviewParserTests(unittest.TestCase):
    def test_unbalanced_message_does_not_swallow_the_next_post(self) -> None:
        markup = """
        <div class="tgme_widget_message" data-post="testcommunity/40">
          <div class="tgme_widget_message_text">Broken workshop
        <div class="tgme_widget_message" data-post="testcommunity/41">
          <div class="tgme_widget_message_text">Valid workshop 20 Sep, 3pm, $5</div>
        </div>
        """
        parser = TelegramPreviewParser()
        parser.feed(markup)
        self.assertEqual(
            ["testcommunity/41"],
            [message.post_path for message in parser.messages],
        )

    def test_extracts_public_message_without_media_or_page_dump(self) -> None:
        markup = """
        <a class="tme_messages_more" href="/s/testcommunity?before=41"></a>
        <div class="tgme_widget_message" data-post="testcommunity/42">
          <div class="tgme_widget_message_text">
            Teen Art Workshop<br>13 September 2026, 2pm<br>
            Bishan CC 579799<br>Ages 13-17<br>Free
            <a href="https://go.gov.sg/example">Register</a>
          </div>
          <time datetime="2026-09-02T01:00:00+00:00"></time>
        </div>
        """
        parser = TelegramPreviewParser()
        parser.feed(markup)
        self.assertEqual("https://t.me/s/testcommunity?before=41", parser.previous_url)
        self.assertEqual(1, len(parser.messages))

        candidate = message_to_candidate(parser.messages[0], SOURCE)
        assert candidate is not None
        self.assertEqual("https://t.me/testcommunity/42", candidate["source_url"])
        self.assertEqual("unverified", candidate["verification"])
        self.assertFalse(candidate["is_fictional"])
        self.assertEqual(["13 September 2026"], candidate["detected"]["dates"])
        self.assertIn("2pm", candidate["detected"]["times"])
        self.assertIn("Free", candidate["detected"]["costs"])
        self.assertIn("Ages 13-17", candidate["detected"]["ages"])
        self.assertEqual(["579799"], candidate["detected"]["postal_codes"])
        self.assertEqual(["https://go.gov.sg/example"], candidate["registration_urls"])
        self.assertNotIn("<div", candidate["excerpt"])
        self.assertLessEqual(len(candidate["excerpt"]), 280)

    def test_ignores_non_event_chatter(self) -> None:
        markup = """
        <div class="tgme_widget_message" data-post="testcommunity/43">
          <div class="tgme_widget_message_text">Thanks for following us!</div>
        </div>
        """
        parser = TelegramPreviewParser()
        parser.feed(markup)
        self.assertIsNone(message_to_candidate(parser.messages[0], SOURCE))

    def test_candidate_id_is_stable_and_content_changes_are_detectable(self) -> None:
        markup = """
        <div class="tgme_widget_message" data-post="testcommunity/44">
          <div class="tgme_widget_message_text">Workshop 20 Sep, 3pm, $5</div>
        </div>
        """
        parser = TelegramPreviewParser()
        parser.feed(markup)
        first = message_to_candidate(parser.messages[0], SOURCE)
        parser = TelegramPreviewParser()
        parser.feed(markup.replace("$5", "$6"))
        second = message_to_candidate(parser.messages[0], SOURCE)
        assert first is not None and second is not None
        self.assertEqual(first["candidate_id"], second["candidate_id"])
        self.assertNotEqual(first["content_sha256"], second["content_sha256"])


if __name__ == "__main__":
    unittest.main()
