/**
 * portfolio_sync.gs — pushes the "PORTEFEUILLE" holdings table from this
 * Google Sheet to real_holdings.json in the Stocazzo GitHub repo, so the
 * Stocazzo tool (and Claude) can read Paul's real ME-DIRECT positions
 * without needing live access to this sheet.
 *
 * SETUP:
 *   1. Open this spreadsheet → Extensions → Apps Script.
 *   2. Paste this whole file in, replacing the default Code.gs content.
 *   3. Project Settings (gear icon) → Script Properties → add:
 *        GITHUB_TOKEN = <a GitHub PAT with contents:write on paulRenDev/Stocazzo>
 *      Create a fine-grained token at https://github.com/settings/tokens
 *      scoped to just this one repo, "Contents" permission = Read and write.
 *   4. Run `pushHoldingsToGitHub` once manually (Run ▶) and grant the
 *      requested permissions (it needs to call out to api.github.com).
 *   5. Run `createDailyTrigger` once to schedule a daily push (07:00).
 *      Re-run `pushHoldingsToGitHub` any time from the Apps Script editor
 *      to push immediately after editing the sheet.
 */

const GITHUB_OWNER     = 'paulRenDev';
const GITHUB_REPO      = 'Stocazzo';
const GITHUB_BRANCH    = 'main';
const GITHUB_FILE_PATH = 'real_holdings.json';

function pushHoldingsToGitHub() {
  const token = PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN');
  if (!token) {
    throw new Error('GITHUB_TOKEN not set — see setup instructions at the top of this file.');
  }

  const holdings = extractHoldings();
  if (!holdings.length) {
    throw new Error('No holdings found — check that the "PORTEFEUILLE" table still has a TICKER column and data rows.');
  }

  const payload = {
    generated_at: new Date().toISOString(),
    source: 'Google Sheets — portfolio_sync.gs',
    holdings: holdings,
  };

  const contentB64 = Utilities.base64Encode(
    JSON.stringify(payload, null, 2),
    Utilities.Charset.UTF_8
  );
  const apiUrl = `https://api.github.com/repos/${GITHUB_OWNER}/${GITHUB_REPO}/contents/${GITHUB_FILE_PATH}`;

  // Need the current file's SHA to update it (GitHub Contents API requirement).
  let sha = null;
  const getResp = UrlFetchApp.fetch(`${apiUrl}?ref=${GITHUB_BRANCH}`, {
    headers: { Authorization: `token ${token}` },
    muteHttpExceptions: true,
  });
  if (getResp.getResponseCode() === 200) {
    sha = JSON.parse(getResp.getContentText()).sha;
  } else if (getResp.getResponseCode() !== 404) {
    throw new Error(`GitHub GET failed: ${getResp.getResponseCode()} ${getResp.getContentText()}`);
  }

  const body = {
    message: `chore: sync real_holdings.json from Google Sheets [skip ci]`,
    content: contentB64,
    branch: GITHUB_BRANCH,
  };
  if (sha) body.sha = sha;

  const putResp = UrlFetchApp.fetch(apiUrl, {
    method: 'put',
    contentType: 'application/json',
    headers: { Authorization: `token ${token}` },
    payload: JSON.stringify(body),
    muteHttpExceptions: true,
  });

  const code = putResp.getResponseCode();
  if (code !== 200 && code !== 201) {
    throw new Error(`GitHub PUT failed: ${code} ${putResp.getContentText()}`);
  }
  Logger.log(`Pushed ${holdings.length} holdings to ${GITHUB_FILE_PATH} (HTTP ${code}).`);
}

/**
 * Scans every sheet in this spreadsheet for the "PORTEFEUILLE" section
 * (the aggregated table with a Name/TICKER/EXCHANGE header row), and
 * returns its rows as [{ticker, name, exchange, currency, shares, value_eur}, ...].
 * Stops at the first blank row or a row whose Name cell is "Watchlist".
 */
function extractHoldings() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  for (const sheet of ss.getSheets()) {
    const data = sheet.getDataRange().getValues();

    // Find the header row: a row containing both "TICKER" and "EXCHANGE".
    let headerRow = -1;
    for (let i = 0; i < data.length; i++) {
      const rowStr = data[i].map(c => String(c).trim().toUpperCase());
      if (rowStr.includes('TICKER') && rowStr.includes('EXCHANGE') && rowStr.includes('NBR')) {
        headerRow = i;
        break;
      }
    }
    if (headerRow === -1) continue;

    const headers = data[headerRow].map(c => String(c).trim());
    const col = {};
    headers.forEach((h, idx) => { if (h) col[h.toUpperCase()] = idx; });

    const holdings = [];
    for (let i = headerRow + 1; i < data.length; i++) {
      const row = data[i];
      const name = String(row[col['NAME']] || '').trim();
      const ticker = String(row[col['TICKER']] || '').trim();

      if (!name && !ticker) break;                 // blank row → end of table
      if (/^watchlist$/i.test(name)) break;         // next section starts
      if (!ticker) continue;                        // skip rows without a ticker

      holdings.push({
        ticker: ticker,
        name: name.replace(/\s*-\s*ME-DIRECT\s*$/i, ''),
        exchange: String(row[col['EXCHANGE']] || '').trim(),
        currency: String(row[col['CURRENCY']] || '').trim(),
        shares: Number(row[col['NBR']] || 0),
        value_eur: col['VALUEEUR'] !== undefined ? Number(row[col['VALUEEUR']] || 0) : null,
      });
    }
    if (holdings.length) return holdings;
  }
  return [];
}

function createDailyTrigger() {
  // Remove any existing triggers for this function first, so re-running
  // this setup step doesn't stack up duplicate daily pushes.
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'pushHoldingsToGitHub')
    .forEach(t => ScriptApp.deleteTrigger(t));

  ScriptApp.newTrigger('pushHoldingsToGitHub')
    .timeBased()
    .everyDays(1)
    .atHour(7)
    .create();

  Logger.log('Daily trigger created (07:00).');
}
