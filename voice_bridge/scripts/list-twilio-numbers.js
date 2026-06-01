import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log('🔍 Fetching all Incoming Phone Numbers from Twilio...');
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers.json`;
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
  console.log('📱 TWILIO INCOMING PHONE NUMBERS');
  console.log('================================================================');
  
  const numbers = data.incoming_phone_numbers || [];
  if (numbers.length === 0) {
    console.log('Nessun numero di telefono acquistato su questo account.');
  } else {
    numbers.forEach(num => {
      console.log(`- Phone Number: ${num.phone_number}`);
      console.log(`  Friendly Name: ${num.friendly_name}`);
      console.log(`  SID: ${num.sid}`);
      console.log(`  Voice Webhook: ${num.voice_url}`);
      console.log('----------------------------------------------------------------');
    });
  }
}

run().catch(err => {
  console.error('\n❌ Failed to fetch phone numbers:', err.message);
  process.exit(1);
});
