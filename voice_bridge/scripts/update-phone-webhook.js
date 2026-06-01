import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const publicBridgeUrl = process.env.PUBLIC_BRIDGE_URL || 'https://c0f4bd94bbbac1f6-217-56-84-96.serveousercontent.com';
const phoneSid = 'PN4d1951797d982a7d04f6c97659dca0cf';

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log(`🚀 Updating Twilio Phone Number (${phoneSid}) voice webhook to: ${publicBridgeUrl}/twilio/inbound...`);
  
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/IncomingPhoneNumbers/${phoneSid}.json`;
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: new URLSearchParams({
      VoiceUrl: `${publicBridgeUrl}/twilio/inbound`,
      VoiceMethod: 'POST'
    }).toString(),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Twilio API failed: ${JSON.stringify(data)}`);
  }

  console.log('✅ Twilio Phone Number voice webhook successfully updated!');
}

run().catch(err => {
  console.error('\n❌ Update failed:', err.message);
  process.exit(1);
});
