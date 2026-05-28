from unittest.mock import MagicMock, patch

import pytest


class TestSMTPNotifyService:
    @pytest.mark.asyncio
    async def test_send_plain_when_no_context(
        self, smtp_service, fake_smtp_client, plain_data
    ):
        await smtp_service.send(plain_data)

        assert len(fake_smtp_client.calls) == 1
        assert fake_smtp_client.calls[0] == {
            "recipient": "test@example.com",
            "subject": "Test subject",
            "plain_content": "Test plain message",
        }

    @pytest.mark.asyncio
    async def test_send_plain_does_not_pass_html_content(
        self, smtp_service, fake_smtp_client, plain_data
    ):
        await smtp_service.send(plain_data)

        assert "html_content" not in fake_smtp_client.calls[0]

    @pytest.mark.asyncio
    async def test_send_html_when_context_provided(
        self,
        smtp_service,
        fake_smtp_client,
        html_data,
        monkeypatch,
    ):
        monkeypatch.setattr(smtp_service, "_render_html", lambda data: "<h1>Test</h1>")

        await smtp_service.send(html_data)

        assert len(fake_smtp_client.calls) == 1
        assert fake_smtp_client.calls[0] == {
            "recipient": "test@example.com",
            "subject": "Test subject",
            "plain_content": "Test plain message",
            "html_content": "<h1>Test</h1>",
        }

    def test_render_html_raises_when_no_context(
        self,
        smtp_service,
        plain_data,
    ):
        with pytest.raises(ValueError, match="Context is required for HTML rendering"):
            smtp_service._render_html(plain_data)

    def test_render_html_calls_template_with_correct_kwargs(
        self,
        smtp_service,
        html_data,
    ):
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Rendered</h1>"

        with patch("services.stmp_notiy_service.template") as mock_tpl:
            mock_tpl.get_template.return_value = mock_template
            result = smtp_service._render_html(html_data)

        mock_tpl.get_template.assert_called_once_with("email/notification.html")
        mock_template.render.assert_called_once_with(
            title="Test title",
            subject="Test subject",
            message="Test plain message",
            action_url="https://example.com",
            action_text="Open It",
            preheader="Test preheader",
            recipient="test@example.com",
        )
        assert result == "<h1>Rendered</h1>"
