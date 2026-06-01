import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function searchNumbers(areaCode = null) {
  let url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}/AvailablePhoneNumbers/IT/Local.json?Limit=5`;
  if (areaCode) {
    url += `&AreaCode=${areaCode}`;
  }
  
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Authorization: authHeader,
    }
  });

  const data = await response.json();
  if (!response.ok) {
    // If no numbers in this area code, return empty array
    if (data.code === 20003 || data.status === 404) {
      return [];
    }
    throw new Error(`Twilio API failed: ${JSON.stringify(data)}`);
  }
  return data.available_phone_numbers || [];
}

async function run() {
  console.log('🔍 Avvio ricerca numeri di telefono italiani su Twilio via API...\n');

  const areasToTry = [
    { code: '0968', name: 'Lamezia Terme' },
    { code: '0984', name: 'Cosenza' },
    { code: '0965', name: 'Reggio Calabria' },
    { code: '02', name: 'Milano' },
    { code: '06', name: 'Roma' }
  ];

  for (const area of areasToTry) {
    console.log(`Searching in Area Code ${area.code} (${area.name})...`);
    try {
      const results = await searchNumbers(area.code);
      if (results.length === 0) {
        console.log(`❌ Nessun numero disponibile per il prefisso ${area.code}.\n`);
      } else {
        console.log(`✅ Trovati numeri disponibili per il prefisso ${area.code}!`);
        results.forEach(num => {
          console.log(`   - ${num.phone_number} (Costo: $1.00/mese)`);
        });
        console.log('');
      }
    } catch (err) {
      console.error(`⚠️ Errore durante la ricerca per ${area.code}:`, err.message, '\n');
    }
  }

  console.log('Searching general Italian local numbers without area code filter...');
  try {
    const generalResults = await searchNumbers();
    if (generalResults.length === 0) {
      console.log('❌ Nessun numero generico trovato.');
    } else {
      console.log('✅ Numeri generici disponibili trovati:');
      generalResults.forEach(num => {
        console.log(`   - ${num.phone_number} (Prefisso: ${num.phone_number.substring(3, 6)})`);
      });
    }
  } catch (err) {
    console.error('⚠️ Errore ricerca generica:', err.message);
  }
}

run().catch(err => {
  console.error('\n❌ Search script failed:', err.message);
  process.exit(1);
});
