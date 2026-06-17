worker start

```shell
cd src/
faststream run workers.smtp_worker:app
```
Ось конкретні приклади того, що передавати в шаблон:
Підтвердження email
```python
context = {
    "type": "Account",
    "subject": "Confirm your email address",
    "message": "Thanks for signing up. Click the button below to verify your email address and activate your account.",
    "action_url": "https://example.com/verify?token=abc123",
    "action_text": "Verify email",
    "recipient": "john@gmail.com"
}
```

Скидання пароля
```python
context = {
    "type": "Security",
    "subject": "Reset your password",
    "message": "We received a request to reset your password. This link expires in 30 minutes. If you didn't request this, you can safely ignore this email.",
    "action_url": "https://example.com/reset?token=xyz789",
    "action_text": "Reset password",
    "recipient": "john@gmail.com"
}
```

Запрошення в команду
```python
context = {
    "type": "Invitation",
    "subject": "Anna invited you to join Acme workspace",
    "message": "Anna Davis has invited you to collaborate in the Acme workspace. Accept the invitation to get started.",
    "action_url": "https://example.com/invite?token=def456",
    "action_text": "Accept invitation",
    "recipient": "john@gmail.com"
}
```

Невдала оплата
```python
context = {
    "type": "Billing",
    "subject": "Payment failed",
    "message": "We couldn't charge your card ending in 4242 for $49.00. Please update your payment method to avoid interruption of your service.",
    "action_url": "https://example.com/billing",
    "action_text": "Update payment",
    "recipient": "john@gmail.com"
}
```

Без кнопки — просто сповіщення
```python
context = {
    "type": "Security",
    "subject": "New login from Chrome on macOS",
    "message": "We detected a new sign-in to your account on Saturday, May 23 at 14:32 from Kyiv, Ukraine. If this was you, no action is needed.",
    "action_url": None,
    "recipient": "john@gmail.com"
}
```


### TELEGRAM Data

massage with reply  keyboard

```JSON
{
  "message": "Your account was updated successfully",
  "type": "telegram",
  "chat_id": 1213212,
  "reply_markup": {
    "keyboard": [
      ["button1", "button2"],
      ["button3"]
    ]
  }
}
```



massage with inline keyboard

```json

{
  "message": "Your account was updated successfully",
  "type": "telegram",
  "chat_id": 1213212,
  "reply_markup": {
    "inline_keyboard": [
      [
        {
          "text": "Approve",
          "callback_data": "approve"
        },
        {
          "text": "Reject",
          "callback_data": "reject"
        }
      ]
    ]
  }
}
```
