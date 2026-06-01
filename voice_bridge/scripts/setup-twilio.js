import { Buffer } from 'node:buffer';

const accountSid = process.env.TWILIO_ACCOUNT_SID;
const authToken = process.env.TWILIO_AUTH_TOKEN;
const publicBridgeUrl = process.env.PUBLIC_BRIDGE_URL || 'https://d8c827c4fb878c.lhr.life';

if (!accountSid || !authToken) {
  console.error('Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set in your .env file');
  process.exit(1);
}

const authHeader = `Basic ${Buffer.from(`${accountSid}:${authToken}`).toString('base64')}`;

async function twilioRequest(path, method = 'POST', bodyParams = {}) {
  const url = `https://api.twilio.com/2010-04-01/Accounts/${accountSid}${path}`;
  const response = await fetch(url, {
    method,
    headers: {
      Authorization: authHeader,
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: method === 'GET' ? undefined : new URLSearchParams(bodyParams).toString(),
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Twilio API ${path} failed: ${JSON.stringify(data)}`);
  }
  return data;
}

async function run() {
  console.log('🚀 Starting automated Twilio Setup for CasaFolino...');
  
  let ipAclSid = null;
  
  // 1. Create or Find IP Access Control List
  try {
    console.log('Step 1: Creating IP Access Control List "Ehiweb VivaVox"...');
    const acl = await twilioRequest('/SIP/IpAccessControlLists.json', 'POST', {
      FriendlyName: 'Ehiweb VivaVox'
    });
    ipAclSid = acl.sid;
    console.log(`✅ IP ACL created with SID: ${ipAclSid}`);
  } catch (err) {
    if (err.message.includes('already exists') || err.message.includes('Conflict')) {
      console.log('ℹ️ IP ACL "Ehiweb VivaVox" already exists. Fetching existing ones...');
      const list = await twilioRequest('/SIP/IpAccessControlLists.json', 'GET');
      const existing = list.ip_access_control_lists?.find(a => a.friendly_name === 'Ehiweb VivaVox');
      if (existing) {
        ipAclSid = existing.sid;
        console.log(`✅ Found existing IP ACL: ${ipAclSid}`);
      }
    }
    if (!ipAclSid) {
      throw err;
    }
  }

  // 2. Add Ehiweb Server IP to IP Access Control List
  try {
    console.log('Step 2: Whitelisting Ehiweb IP (79.98.45.133) in the ACL...');
    await twilioRequest(`/SIP/IpAccessControlLists/${ipAclSid}/IpAddresses.json`, 'POST', {
      FriendlyName: 'VivaVox SIP Server',
      IpAddress: '79.98.45.133',
      PrefixLength: '32'
    });
    console.log('✅ Whitelisted IP 79.98.45.133 successfully');
  } catch (err) {
    if (err.message.includes('already exists') || err.message.includes('Conflict')) {
      console.log('ℹ️ IP 79.98.45.133 was already whitelisted in this ACL.');
    } else {
      throw err;
    }
  }

  // 3. Create or Update SIP Domain "casafolino"
  let domainSid = null;
  const desiredDomain = 'casafolino.sip.twilio.com';
  
  try {
    console.log(`Step 3: Creating SIP Domain "${desiredDomain}" pointing to "${publicBridgeUrl}/twilio/inbound"...`);
    const domain = await twilioRequest('/SIP/Domains.json', 'POST', {
      DomainName: desiredDomain,
      FriendlyName: 'CasaFolino SIP',
      VoiceUrl: `${publicBridgeUrl}/twilio/inbound`,
      VoiceMethod: 'POST'
    });
    domainSid = domain.sid;
    console.log(`✅ SIP Domain created successfully with SID: ${domainSid}`);
  } catch (err) {
    if (err.message.includes('already exists') || err.message.includes('Conflict')) {
      console.log('ℹ️ SIP Domain already exists. Fetching domain SID to update webhook...');
      const list = await twilioRequest('/SIP/Domains.json', 'GET');
      const existing = list.sip_domains?.find(d => d.domain_name === desiredDomain);
      if (existing) {
        domainSid = existing.sid;
        console.log(`✅ Found existing SIP Domain: ${domainSid}. Updating webhook URL...`);
        await twilioRequest(`/SIP/Domains/${domainSid}.json`, 'POST', {
          VoiceUrl: `${publicBridgeUrl}/twilio/inbound`,
          VoiceMethod: 'POST'
        });
        console.log('✅ Webhook URL successfully updated');
      }
    }
    if (!domainSid) {
      throw err;
    }
  }

  // 4. Map IP ACL to SIP Domain
  try {
    console.log('Step 4: Mapping the Ehiweb IP ACL to the SIP Domain...');
    await twilioRequest(`/SIP/Domains/${domainSid}/IpAccessControlListMappings.json`, 'POST', {
      IpAccessControlListSid: ipAclSid
    });
    console.log('✅ IP ACL successfully mapped to SIP Domain');
  } catch (err) {
    if (err.message.includes('already exists') || err.message.includes('Conflict')) {
      console.log('ℹ️ IP ACL was already mapped to this SIP Domain.');
    } else {
      throw err;
    }
  }

  console.log('\n🎉 TWILIO PBX AUTOMATED CONFIGURATION COMPLETED SUCCESSFULLY!');
  console.log(`📞 You can now forward Ehiweb to: sip:inbound@${desiredDomain}`);
}

run().catch(err => {
  console.error('\n❌ Twilio Setup failed:', err.message);
  process.exit(1);
});
