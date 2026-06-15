from unittest.mock import ANY, MagicMock, patch

import pytest


class TestSTMPNotifyService:
    @pytest.mark.asyncio
    async def test_send_plain_when_no_context(
        self, smtp_service, fake_smtp_client, email_payload_no_content
    ):
        await smtp_service.send(email_payload_no_content)

        assert len(fake_smtp_client.calls) == 1
        assert fake_smtp_client.calls[0] == {
            "recipient": "test@example.com",
            "subject": "Test subject",
            "plain_content": "Test plain message",
        }

    @pytest.mark.asyncio
    async def test_send_plain_does_not_pass_html_content(
        self, smtp_service, fake_smtp_client, email_payload_no_content
    ):
        await smtp_service.send(email_payload_no_content)

        assert "html_content" not in fake_smtp_client.calls[0]

    @pytest.mark.asyncio
    async def test_send_html_when_context_provided(
        self,
        smtp_service,
        fake_smtp_client,
        email_payload_with_content,
        monkeypatch,
    ):
        monkeypatch.setattr(smtp_service, "_render_html", lambda data: "<h1>Test</h1>")

        await smtp_service.send(email_payload_with_content)

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
        email_payload_no_content,
    ):
        with pytest.raises(ValueError, match="Context is required for HTML rendering"):
            smtp_service._render_html(email_payload_no_content)

    def test_render_html_calls_template_with_correct_kwargs(
        self,
        smtp_service,
        email_payload_with_content,
    ):
        mock_template = MagicMock()
        mock_template.render.return_value = "<h1>Rendered</h1>"

        with patch("services.smtp_notify_service.template") as mock_tpl:
            mock_tpl.get_template.return_value = mock_template
            result = smtp_service._render_html(email_payload_with_content)

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

    @pytest.mark.asyncio
    async def test_renders_real_notification_template(
        self,
        smtp_service,
        fake_smtp_client,
        email_payload_with_content,
    ):
        await smtp_service.send(email_payload_with_content)

        assert len(fake_smtp_client.calls) == 1

        # verify smtp payload
        call = fake_smtp_client.calls[0]

        assert call == {
            "recipient": email_payload_with_content.recipient,
            "subject": email_payload_with_content.subject,
            "plain_content": email_payload_with_content.message,
            "html_content": ANY,
        }

        # verify rendered html content
        html = call["html_content"]
        context = email_payload_with_content.context

        assert context is not None

        assert context.title in html
        assert context.action_text in html
        assert f'href="{context.action_url}"' in html
        assert context.preheader in html

        assert email_payload_with_content.message in html
        assert email_payload_with_content.subject in html
        assert email_payload_with_content.recipient in html

    @pytest.mark.asyncio
    async def test_renders_notify_template_not_button(
        self,
        smtp_service,
        fake_smtp_client,
        email_payload_with_content,
    ):
        data = email_payload_with_content.model_copy(
            update={
                "context": email_payload_with_content.context.model_copy(
                    update={
                        "action_text": None,
                        "action_url": None,
                    }
                )
            }
        )

        await smtp_service.send(data)

        html = fake_smtp_client.calls[0]["html_content"]

        # core content
        assert data.context.title in html
        assert data.message in html
        assert data.subject in html

        # button must NOT exist
        assert email_payload_with_content.context.action_url not in html
        assert email_payload_with_content.context.action_text not in html
        assert 'href="None"' not in html
        assert ">None<" not in html
