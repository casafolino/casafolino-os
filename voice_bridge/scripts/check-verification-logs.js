import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log('🔍 Fetching recent call logs from Twilio...');
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/Calls.json?Limit=5`;
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
  console.log('📞 TWILIO RECENT CALL LOGS');
  console.log('================================================================');
  
  const calls = data.calls || [];
  if (calls.length === 0) {
    console.log('Nessuna chiamata trovata nei log.');
  } else {
    calls.forEach(call => {
      console.log(`- From: ${call.from}`);
      console.log(`  To: ${call.to}`);
      console.log(`  Status: ${call.status}`);
      console.log(`  Duration: ${call.duration}s`);
      console.log(`  Price: ${call.price} ${call.price_unit || ''}`);
      console.log(`  Direction: ${call.direction}`);
      console.log(`  Date Created: ${call.date_created}`);
      console.log(`  Error Code: ${call.subresource_uris?.notifications ? 'check notifications' : 'none'}`);
      console.log('----------------------------------------------------------------');
    });
  }
}

run().catch(err => {
  console.error('\n❌ Failed to fetch call logs:', err.message);
  process.exit(1);
});
