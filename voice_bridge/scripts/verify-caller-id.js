import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const phoneNumber = process.env.TWILIO_PHONE_NUMBER || '+3909681660200';

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log(`📞 Initiating Twilio Caller ID Verification for Ehiweb number: ${phoneNumber}...`);
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/OutgoingCallerIds.json`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      PhoneNumber: phoneNumber,
      FriendlyName: 'CasaFolino Ehiweb',
    }).toString(),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Twilio API failed to request validation: ${JSON.stringify(data)}`);
  }

  console.log('\n================================================================');
  console.log('🔴 TWILIO CALLER ID VERIFICATION TRIGGERED SUCCESSFULLY!');
  console.log('================================================================\n');
  console.log(`📱 Il tuo telefono (numero Ehiweb ${phoneNumber}) sta per squillare!`);
  console.log(`🔑 Quando rispondi, inserisci sulla tastiera del telefono questo codice di verifica:`);
  console.log(`\n👉   ${data.validation_code}   👈\n`);
  console.log('================================================================');
  console.log('Rimango in attesa che tu risponda alla chiamata e digiti il codice...');
}

run().catch(err => {
  console.error('\n❌ Caller ID Verification failed:', err.message);
  process.exit(1);
});
