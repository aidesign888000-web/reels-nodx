const base = () => `${process.env.SUPABASE_URL}/rest/v1`;
const headers = (extra = {}) => ({
  apikey: process.env.SUPABASE_SERVICE_ROLE_KEY,
  Authorization: `Bearer ${process.env.SUPABASE_SERVICE_ROLE_KEY}`,
  'Content-Type': 'application/json',
  ...extra,
});

async function rest(path, { method = 'GET', body, prefer } = {}) {
  const res = await fetch(`${base()}/${path}`, {
    method,
    headers: headers(prefer ? { Prefer: prefer } : {}),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Supabase ${res.status}: ${await res.text()}`);
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

async function upsertContact(phone, name) {
  const rows = await rest('contacts?on_conflict=phone', {
    method: 'POST',
    prefer: 'resolution=merge-duplicates,return=representation',
    body: { phone, ...(name ? { name } : {}), updated_at: new Date().toISOString() },
  });
  return rows[0];
}

const updateContact = (id, fields) =>
  rest(`contacts?id=eq.${id}`, {
    method: 'PATCH',
    prefer: 'return=representation',
    body: { ...fields, updated_at: new Date().toISOString() },
  }).then((r) => r[0]);

async function saveMessage(contact_id, role, content, wamid) {
  return rest('messages?on_conflict=wamid', {
    method: 'POST',
    prefer: 'resolution=ignore-duplicates,return=representation',
    body: { contact_id, role, content, wamid: wamid || null },
  });
}

async function history(contact_id, limit = 20) {
  const rows = await rest(
    `messages?contact_id=eq.${contact_id}&select=role,content&order=created_at.desc&limit=${limit}`
  );
  return rows.reverse();
}

const saveAppointment = (row) => rest('appointments', { method: 'POST', body: row });

module.exports = { upsertContact, updateContact, saveMessage, history, saveAppointment };
