# Agente IA de WhatsApp (YCloud + Supabase + Netlify)

Flujo: WhatsApp → YCloud → webhook (Netlify background function) → Claude (con herramientas de calendario y CRM) → respuesta por YCloud.
Cero dependencias npm. CRM = tabla `contacts` en Supabase (+ `CRM_WEBHOOK_URL` opcional para HubSpot/Zoho/Make).

## Pasos
1. **Supabase**: crea proyecto → SQL Editor → pega `supabase/schema.sql` → Run. Copia `Project URL` y la `service_role key` (Settings > API).
2. **Google Calendar**: Google Cloud > crea Service Account > crea llave JSON. En tu calendario > Compartir con el email de la cuenta de servicio con permiso "Hacer cambios en eventos". El ID del calendario está en Configuración del calendario.
3. **Netlify**: Add new site > Import from Git > repo `reels-nodx`, rama de este código, **Base directory: `whatsapp-agent`**. Luego Site configuration > Environment variables: pega las de `.env.example`. Redeploy.
4. **YCloud**: Developers > Webhooks > Add endpoint con URL `https://TU-SITIO.netlify.app/.netlify/functions/webhook-background`, evento `whatsapp.inbound_message.received`. Copia el signing secret a `YCLOUD_WEBHOOK_SECRET`. API key en Developers > API Keys.
5. **Prueba**: escribe al número desde otro celular.

`GOOGLE_PRIVATE_KEY`: pega el valor `private_key` del JSON tal cual (con los `\n`).
