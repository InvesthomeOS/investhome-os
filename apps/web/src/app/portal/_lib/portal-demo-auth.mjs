/**
 * Local-development portal demo login only.
 * Never enabled when NODE_ENV=production. Passwords come from env, not source.
 */

function readEnv(env, name) {
  const value = env?.[name];
  return typeof value === 'string' ? value.trim() : '';
}

export function isPortalDemoAuthEnabled(env = process.env) {
  if (readEnv(env, 'NODE_ENV').toLowerCase() === 'production') {
    return false;
  }
  const flag = readEnv(env, 'PORTAL_DEMO_AUTH').toLowerCase();
  return flag === '1' || flag === 'true' || flag === 'yes';
}

export function listPortalDemoAccounts(env = process.env) {
  if (!isPortalDemoAuthEnabled(env)) {
    return [];
  }
  const passwordA = readEnv(env, 'PORTAL_DEMO_PASSWORD');
  const emailA = readEnv(env, 'PORTAL_DEMO_EMAIL');
  const investorA = readEnv(env, 'PORTAL_DEMO_INVESTOR_ID') || 'portal-inv-a';
  const passwordB = readEnv(env, 'PORTAL_DEMO_PASSWORD_B') || passwordA;
  const emailB = readEnv(env, 'PORTAL_DEMO_EMAIL_B');
  const investorB = readEnv(env, 'PORTAL_DEMO_INVESTOR_ID_B') || 'portal-inv-b';
  const accounts = [];
  if (emailA && passwordA) {
    accounts.push({ email: emailA.toLowerCase(), password: passwordA, investorId: investorA });
  }
  if (emailB && passwordB) {
    accounts.push({ email: emailB.toLowerCase(), password: passwordB, investorId: investorB });
  }
  return accounts;
}

export function authenticatePortalDemo(email, password, env = process.env) {
  if (!isPortalDemoAuthEnabled(env)) {
    return null;
  }
  const submittedEmail = String(email || '').trim().toLowerCase();
  const submittedPassword = String(password || '');
  if (!submittedEmail || !submittedPassword) {
    return null;
  }
  const match = listPortalDemoAccounts(env).find(
    (account) => account.email === submittedEmail && account.password === submittedPassword,
  );
  if (!match) {
    return null;
  }
  return {
    investorId: match.investorId,
    email: match.email,
    issuedAt: new Date().toISOString(),
  };
}
