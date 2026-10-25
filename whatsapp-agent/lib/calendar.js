const crypto = require('crypto');
const TZ = () => process.env.TIMEZONE || 'America/Bogota';
const CAL = () => encodeURIComponent(process.env.GOOGLE_CALENDAR_ID);

async function token() {
  const b64 = (o) => Buffer.from(JSON.stringify(o)).toString('base64url');
  const now = Math.floor(Date.now() / 1000);
  const unsigned = `${b64({ alg: 'RS256', typ: 'JWT' })}.${b64({
    iss: process.env.GOOGLE_SERVICE_ACCOUNT_EMAIL,
    scope: 'https://www.googleapis.com/auth/calendar',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  })}`;
  const key = process.env.GOOGLE_PRIVATE_KEY.replace(/\\n/g, '\n');
  const sig = crypto.createSign('RSA-SHA256').update(unsigned).sign(key, 'base64url');
  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: `${unsigned}.${sig}`,
    }),
  });
  if (!res.ok) throw new Error(`Google auth ${res.status}: ${await res.text()}`);
  return (await res.json()).access_token;
}

async function gcal(path, opts = {}) {
  const res = await fetch(`https://www.googleapis.com/calendar/v3/calendars/${CAL()}${path}`, {
    ...opts,
    headers: { Authorization: `Bearer ${await token()}`, 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error(`Calendar ${res.status}: ${await res.text()}`);
  return res.json();
}

// Horarios ocupados entre dos fechas ISO.
async function busy(fromISO, toISO) {
  const res = await fetch('https://www.googleapis.com/calendar/v3/freeBusy', {
    method: 'POST',
    headers: { Authorization: `Bearer ${await token()}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({
      timeMin: fromISO,
      timeMax: toISO,
      timeZone: TZ(),
      items: [{ id: process.env.GOOGLE_CALENDAR_ID }],
    }),
  });
  if (!res.ok) throw new Error(`FreeBusy ${res.status}: ${await res.text()}`);
  const data = await res.json();
  return data.calendars[process.env.GOOGLE_CALENDAR_ID].busy;
}

async function createEvent({ title, startISO, endISO, description }) {
  return gcal('/events', {
    method: 'POST',
    body: JSON.stringify({
      summary: title,
      description,
      start: { dateTime: startISO, timeZone: TZ() },
      end: { dateTime: endISO, timeZone: TZ() },
    }),
  });
}

module.exports = { busy, createEvent };
