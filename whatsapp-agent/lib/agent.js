const db = require('./supabase');
const cal = require('./calendar');
const crm = require('./crm');

const MODEL = 'claude-sonnet-5-5';
const TZ = () => process.env.TIMEZONE || 'America/Bogota';

const tools = [
  {
    name: 'consultar_disponibilidad',
    description: 'Devuelve los bloques OCUPADOS del calendario entre dos fechas. Lo que no esté ocupado está libre.',
    input_schema: {
      type: 'object',
      properties: {
        desde: { type: 'string', description: 'ISO 8601 con zona horaria' },
        hasta: { type: 'string', description: 'ISO 8601 con zona horaria' },
      },
      required: ['desde', 'hasta'],
    },
  },
  {
    name: 'agendar_cita',
    description: 'Crea la cita en el calendario. Úsala solo después de que el cliente confirme día y hora y de haber verificado disponibilidad.',
    input_schema: {
      type: 'object',
      properties: {
        titulo: { type: 'string' },
        inicio: { type: 'string', description: 'ISO 8601 con zona horaria' },
        duracion_min: { type: 'integer', default: 30 },
      },
      required: ['titulo', 'inicio'],
    },
  },
  {
    name: 'guardar_datos_cliente',
    description: 'Guarda en el CRM nombre, email, estado y notas del cliente.',
    input_schema: {
      type: 'object',
      properties: {
        nombre: { type: 'string' },
        email: { type: 'string' },
        estado: { type: 'string', enum: ['nuevo', 'interesado', 'cita_agendada', 'cliente', 'descartado'] },
        notas: { type: 'string' },
      },
    },
  },
];

async function runTool(name, input, contact) {
  if (name === 'consultar_disponibilidad') {
    return { ocupado: await cal.busy(input.desde, input.hasta) };
  }
  if (name === 'agendar_cita') {
    const start = new Date(input.inicio);
    const end = new Date(start.getTime() + (input.duracion_min || 30) * 60000);
    const ev = await cal.createEvent({
      title: input.titulo,
      startISO: start.toISOString(),
      endISO: end.toISOString(),
      description: `Cliente: ${contact.name || ''} ${contact.phone}`,
    });
    await db.saveAppointment({
      contact_id: contact.id,
      google_event_id: ev.id,
      starts_at: start.toISOString(),
      ends_at: end.toISOString(),
      title: input.titulo,
    });
    await crm.saveLead(contact, { status: 'cita_agendada' });
    return { ok: true, evento: ev.htmlLink };
  }
  if (name === 'guardar_datos_cliente') {
    const f = {};
    if (input.nombre) f.name = input.nombre;
    if (input.email) f.email = input.email;
    if (input.estado) f.status = input.estado;
    if (input.notas) f.notes = input.notas;
    await crm.saveLead(contact, f);
    return { ok: true };
  }
  return { error: 'herramienta desconocida' };
}

function system() {
  const now = new Date().toLocaleString('es-CO', { timeZone: TZ(), dateStyle: 'full', timeStyle: 'short' });
  return `Eres el asistente de WhatsApp de ${process.env.BUSINESS_NAME || 'la empresa'}. Respondes en español, breve y cálido (máx. 3 frases por mensaje, sin markdown).
Objetivos: resolver dudas, captar nombre y email del cliente, agendar citas y guardar todo en el CRM.
Ahora es ${now} (zona ${TZ()}). Al agendar, verifica disponibilidad primero, propone 2 horarios y confirma antes de crear la cita.
No inventes precios ni información que no tengas; si no sabes, di que un humano le escribirá.
${process.env.AGENT_INSTRUCTIONS || ''}`;
}

async function reply(contact, userText) {
  const hist = await db.history(contact.id, 20);
  // La API exige que empiece con 'user' y alterne; fusionamos consecutivos del mismo rol.
  const messages = [];
  for (const m of hist) {
    const last = messages[messages.length - 1];
    if (last && last.role === m.role) last.content += `\n${m.content}`;
    else messages.push({ role: m.role, content: m.content });
  }
  while (messages.length && messages[0].role !== 'user') messages.shift();
  if (!messages.length) messages.push({ role: 'user', content: userText });

  for (let i = 0; i < 6; i++) {
    const res = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': process.env.ANTHROPIC_API_KEY,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({ model: MODEL, max_tokens: 600, system: system(), tools, messages }),
    });
    if (!res.ok) throw new Error(`Anthropic ${res.status}: ${await res.text()}`);
    const data = await res.json();
    messages.push({ role: 'assistant', content: data.content });
    if (data.stop_reason !== 'tool_use') {
      return data.content.filter((b) => b.type === 'text').map((b) => b.text).join('\n').trim();
    }
    const results = [];
    for (const b of data.content.filter((x) => x.type === 'tool_use')) {
      let out;
      try {
        out = await runTool(b.name, b.input, contact);
      } catch (e) {
        out = { error: e.message };
      }
      results.push({ type: 'tool_result', tool_use_id: b.id, content: JSON.stringify(out) });
    }
    messages.push({ role: 'user', content: results });
  }
  return 'Dame un momento, un asesor te escribirá enseguida.';
}

module.exports = { reply };
