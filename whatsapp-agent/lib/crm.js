const db = require('./supabase');

// CRM = tablas de Supabase (contacts). Si defines CRM_WEBHOOK_URL, cada cambio
// también se envía por POST (HubSpot/Zoho/Make/n8n/etc.).
async function syncExternal(payload) {
  if (!process.env.CRM_WEBHOOK_URL) return;
  try {
    await fetch(process.env.CRM_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch (e) {
    console.error('CRM webhook falló', e.message);
  }
}

async function saveLead(contact, fields) {
  const updated = await db.updateContact(contact.id, fields);
  await syncExternal({ event: 'contact.updated', contact: updated });
  return updated;
}

module.exports = { saveLead, syncExternal };
