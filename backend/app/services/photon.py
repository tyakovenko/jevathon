"""Texting devs via Photon (iMessage/SMS). Transport only.

Real adapter pending API docs: Photon's SDKs are TypeScript-first (spectrum-ts); the Python/REST
send + inbound-reply (webhook) shapes are unconfirmed. See docs §13 Q4. Don't guess the API.
Inbound replies arrive at POST /webhooks/photon → Orchestrator.on_dev_reply.
"""

from typing import Protocol

from pydantic import BaseModel


class Message(BaseModel):
    to: str
    text: str


class Photon(Protocol):
    async def send(self, to: str, text: str) -> None: ...


class RealPhoton:
    def __init__(self, project_id: str, secret: str) -> None:
        raise NotImplementedError("Photon real adapter not built yet — need Photon API docs (docs §13 Q4)")

    async def send(self, to: str, text: str) -> None:  # pragma: no cover
        raise NotImplementedError


class FakePhoton:
    """Keeps an outbox the dashboard can show (GET /outbox)."""

    def __init__(self) -> None:
        self.outbox: list[Message] = []

    async def send(self, to: str, text: str) -> None:
        self.outbox.append(Message(to=to, text=text))
