// Función "background" de Netlify: responde 202 a YCloud al instante y procesa hasta 15 min.
// URL del webhook en YCloud: https://TU-SITIO.netlify.app/.netlify/functions/webhook-background
const { verifySignature, sendText } = require('../../lib/ycloud');
const db = require('../../lib/supabase');
const { reply } = require('../../lib/agent');

exports.handler = async (event) => {
  if (!verifySignature(event.body || '', event.headers['ycloud-signature'], process.env.YCLOUD_WEBHOOK_SECRET)) {
    console.warn('Firma inválida');
    return { statusCode: 401 };
  }
  let payload;
  try {
    payload = JSON.parse(event.body);
  } catch {
    return { statusCode: 400 };
  }
  if (payload.type !== 'whatsapp.inbound_message.received') return { statusCode: 200 };

  const msg = payload.whatsappInboundMessage;
  try {
    const text =
      msg.type === 'text' ? msg.text?.body : `[el cliente envió un mensaje tipo ${msg.type}; pídele que lo escriba en texto]`;
    const phone = msg.from.startsWith('+') ? msg.from : `+${msg.from}`;
    const contact = await db.upsertContact(phone, msg.customerProfile?.name);
    const saved = await db.saveMessage(contact.id, 'user', text, msg.wamid || msg.id);
    if (!saved || saved.length === 0) return { statusCode: 200 }; // duplicado, ya procesado
    const answer = await reply(contact, text);
    await sendText(phone, answer);
    await db.saveMessage(contact.id, 'assistant', answer);
  } catch (e) {
    console.error('Error procesando mensaje', e);
  }
  return { statusCode: 200 };
};
