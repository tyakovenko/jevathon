import { createServer } from "node:http";
import { Spectrum } from "spectrum-ts";
import { imessage } from "spectrum-ts/providers/imessage";

// Bridges Jevathon's Python backend (no TS-capable Spectrum SDK) to Photon/iMessage.
// Inbound dev replies -> POST backend /webhooks/photon. Outbound texts -> POST /send here.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";
const PORT = Number(process.env.PORT ?? 4001);

const app = await Spectrum({
  projectId: process.env.PROJECT_ID!,
  projectSecret: process.env.PROJECT_SECRET!,
  providers: [imessage.config()],
});
const im = imessage(app);

async function forwardToBackend(from: string, text: string) {
  const res = await fetch(`${BACKEND_URL}/webhooks/photon`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ from, text }),
  });
  if (!res.ok) {
    console.error(`backend rejected inbound reply from ${from}: ${res.status} ${await res.text()}`);
  }
}

// Outbound: POST /send {"to": "+1555...", "text": "..."} — matches services/photon.py's RealPhoton.send.
const server = createServer((req, res) => {
  if (req.method !== "POST" || req.url !== "/send") {
    res.writeHead(404).end();
    return;
  }
  let body = "";
  req.on("data", (chunk) => (body += chunk));
  req.on("end", async () => {
    try {
      const { to, text } = JSON.parse(body);
      const space = await im.space.create(await im.user(to));
      await space.send(text);
      res.writeHead(200, { "Content-Type": "application/json" }).end(JSON.stringify({ ok: true }));
    } catch (err) {
      console.error("send failed:", err);
      res.writeHead(502, { "Content-Type": "application/json" }).end(JSON.stringify({ ok: false, error: String(err) }));
    }
  });
});
server.listen(PORT, () => console.log(`photon-bridge listening on :${PORT} (send) -> backend ${BACKEND_URL} (replies)`));

// Inbound: reactive loop, forwards every dev text reply to the backend.
for await (const [, message] of app.messages) {
  if (message.direction === "outbound") continue;
  if (message.content.type !== "text") continue;
  const from = message.sender?.id;
  if (!from) {
    console.error("inbound text with no sender id, dropping:", message.content.text);
    continue;
  }
  console.log(`inbound from ${from}: ${message.content.text}`);
  await message.react("👍");
  await forwardToBackend(from, message.content.text);
}
