const crypto = require('crypto');

// Firma de YCloud: header "YCloud-Signature: t=<ts>,s=<hmac_sha256(`${t}.${body}`)>"
function verifySignature(rawBody, header, secret) {
  if (!secret) return true; // sin secreto configurado no se valida
  if (!header) return false;
  const parts = Object.fromEntries(header.split(',').map((p) => p.split('=')));
  const expected = crypto.createHmac('sha256', secret).update(`${parts.t}.${rawBody}`).digest('hex');
  try {
    return crypto.timingSafeEqual(Buffer.from(expected), Buffer.from(parts.s || ''));
  } catch {
    return false;
  }
}

async function sendText(to, text) {
  const res = await fetch('https://api.ycloud.com/v2/whatsapp/messages/sendDirectly', {
    method: 'POST',
    headers: { 'X-API-Key': process.env.YCLOUD_API_KEY, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      from: process.env.WHATSAPP_NUMBER,
      to,
      type: 'text',
      text: { body: text },
    }),
  });
  if (!res.ok) throw new Error(`YCloud ${res.status}: ${await res.text()}`);
  return res.json();
}

module.exports = { verifySignature, sendText };
