import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log('🔍 Fetching recent debug/error notifications from Twilio...');
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Notifications.json?Limit=5`;
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: authHeader,
    }
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Twilio API failed: ${JSON.stringify(data)}`);
  }

  console.log('\n================================================================');
  console.log('⚠️ TWILIO RECENT DEBUG/ERROR NOTIFICATIONS');
  console.log('================================================================');
  
  const notes = data.notifications || [];
  if (notes.length === 0) {
    console.log('Nessuna notifica di errore trovata.');
  } else {
    notes.forEach(note => {
      console.log(`- Date: ${note.message_date}`);
      console.log(`  Log Level: ${note.log_level}`);
      console.log(`  Message Text: ${note.message_text}`);
      console.log(`  More Info: ${note.more_info}`);
      console.log('----------------------------------------------------------------');
    });
  }
}

run().catch(err => {
  console.error('\n❌ Failed to fetch notifications:', err.message);
  process.exit(1);
});
