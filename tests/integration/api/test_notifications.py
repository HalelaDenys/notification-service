import pytest


class TestNotificationsApi:
    @pytest.mark.asyncio
    async def test_accepts_plain_notification(
        self,
        async_client,
        fake_notify_service,
        email_payload_no_content,
    ):
        payload = email_payload_no_content

        response = await async_client.post(
            "/api/v1/notifications", json=payload.model_dump()
        )

        assert response.status_code == 202
        assert len(fake_notify_service.calls) == 1

        data = fake_notify_service.calls[0]

        assert data.type == payload.type
        assert data.recipient == payload.recipient
        assert data.subject == payload.subject
        assert data.message == payload.message
        assert data.context is None

    @pytest.mark.asyncio
    async def test_create_notification_without_context(
        self,
        async_client,
        fake_notify_service,
        email_payload_with_content,
    ):
        payload = email_payload_with_content

        response = await async_client.post(
            "/api/v1/notifications", json=payload.model_dump()
        )

        assert response.status_code == 202
        assert len(fake_notify_service.calls) == 1

        data = fake_notify_service.calls[0]

        assert data.context is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "field,value",
        [
            ("recipient", ""),
            ("subject", ""),
            ("message", ""),
        ],
    )
    async def test_validate_error(
        self,
        async_client,
        email_payload_no_content,
        field,
        value,
    ):
        payload = email_payload_no_content.model_copy(update={field: value})

        response = await async_client.post(
            "/api/v1/notifications", json=payload.model_dump()
        )
        data = response.json()

        assert response.status_code == 422
        assert data["detail"][0]["loc"] == ["body", "email", field]

    @pytest.mark.asyncio
    async def test_returns_500_when_notify_service_fails(
        self,
        async_client,
        fake_notify_service,
        email_payload_no_content,
    ):
        fake_notify_service.should_fail = True

        response = await async_client.post(
            "/api/v1/notifications",
            json=email_payload_no_content.model_dump(),
        )

        assert response.status_code == 500
