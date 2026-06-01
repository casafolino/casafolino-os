import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function run() {
  console.log('🔍 Fetching Twilio Regulatory Bundles via API...');
  
  // Note: Regulatory compliance resides in the numbers.twilio.com domain
  const url = 'https://numbers.twilio.com/v2/RegulatoryCompliance/Bundles';
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
  console.log('📋 TWILIO REGULATORY BUNDLES STATUS');
  console.log('================================================================');
  
  const bundles = data.results || [];
  if (bundles.length === 0) {
    console.log('Nessun fascicolo regolatorio (Regulatory Bundle) creato su questo account.');
    console.log('\n💡 Questo spiega perché la ricerca restituisce 0 risultati!');
    console.log('Fino a quando non crei e carichi i documenti del bundle per l\'Italia,');
    console.log('Twilio ti nasconde tutti i numeri italiani disponibili.');
  } else {
    bundles.forEach(b => {
      console.log(`- Bundle Name: ${b.friendly_name}`);
      console.log(`  Status: ${b.status}`);
      console.log(`  SID: ${b.sid}`);
      console.log(`  Regulation: ${b.regulation_sid}`);
      console.log(`  Date Created: ${b.date_created}`);
      console.log('----------------------------------------------------------------');
    });
  }
}

run().catch(err => {
  console.error('\n❌ Failed to fetch regulatory bundles:', err.message);
  process.exit(1);
});
