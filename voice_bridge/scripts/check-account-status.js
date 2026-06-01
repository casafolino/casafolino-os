import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log('🔍 Fetching Twilio Account Status...');
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}.json`;
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
  console.log('📊 TWILIO ACCOUNT DETAILS');
  console.log('================================================================');
  console.log(`- Friendly Name: ${data.friendly_name}`);
  console.log(`- Type: ${data.type}`);
  console.log(`- Status: ${data.status}`);
  console.log(`- Date Created: ${data.date_created}`);
  console.log('================================================================');
}

run().catch(err => {
  console.error('\n❌ Failed to fetch account status:', err.message);
  process.exit(1);
});
