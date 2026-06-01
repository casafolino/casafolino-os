import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log('🔍 Fetching all Outgoing Caller IDs from Twilio...');
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/OutgoingCallerIds.json`;
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
  console.log('📋 TWILIO OUTGOING CALLER IDS');
  console.log('================================================================');
  
  const ids = data.outgoing_caller_ids || [];
  if (ids.length === 0) {
    console.log('Nessun mittente registrato o verificato.');
  } else {
    ids.forEach(id => {
      console.log(`- Phone Number: ${id.phone_number}`);
      console.log(`  Friendly Name: ${id.friendly_name}`);
      console.log(`  SID: ${id.sid}`);
      console.log(`  Date Created: ${id.date_created}`);
      console.log('----------------------------------------------------------------');
    });
  }
}

run().catch(err => {
  console.error('\n❌ Failed to fetch caller IDs:', err.message);
  process.exit(1);
});
