const Database = require('better-sqlite3');
const path = require('path');
const fs = require('fs');

const DB_PATH = path.join(__dirname, '..', 'data', 'leadforge.db');

let db;

function init() {
  const dir = path.dirname(DB_PATH);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

  db = new Database(DB_PATH);
  db.pragma('journal_mode = WAL');
  db.pragma('foreign_keys = ON');

  db.exec(`
    CREATE TABLE IF NOT EXISTS leads (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      company TEXT NOT NULL,
      website TEXT,
      email TEXT,
      phone TEXT,
      address TEXT,
      city TEXT,
      state TEXT,
      country TEXT,
      industry TEXT,
      employees TEXT,
      revenue TEXT,
      social_links TEXT,
      description TEXT,
      source TEXT,
      score INTEGER DEFAULT 0,
      notes TEXT,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS campaigns (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      industry TEXT,
      location TEXT,
      status TEXT DEFAULT 'draft',
      total_leads INTEGER DEFAULT 0,
      scraped_leads INTEGER DEFAULT 0,
      cost REAL DEFAULT 0.00,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS scraped_data (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      url TEXT NOT NULL,
      data TEXT,
      source TEXT,
      campaign_id INTEGER,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS credits (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      balance REAL DEFAULT 0.00,
      total_spent REAL DEFAULT 0.00,
      last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS exports (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      campaign_id INTEGER,
      format TEXT,
      file_path TEXT,
      lead_count INTEGER,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
  `);

  // Initialize default credit balance if empty
  const row = db.prepare('SELECT COUNT(*) as count FROM credits').get();
  if (row.count === 0) {
    db.prepare('INSERT INTO credits (balance) VALUES (0)').run();
  }

  console.log('✅ Database initialized');
  return db;
}

function getDb() {
  if (!db) throw new Error('Database not initialized. Call init() first.');
  return db;
}

function insertLead(lead) {
  const stmt = getDb().prepare(`
    INSERT INTO leads (company, website, email, phone, address, city, state, country, 
                       industry, employees, revenue, social_links, description, source, score)
    VALUES (@company, @website, @email, @phone, @address, @city, @state, @country,
            @industry, @employees, @revenue, @social_links, @description, @source, @score)
  `);
  return stmt.run(lead);
}

function searchLeads(options) {
  const { query, industry, location, limit = 100, offset = 0 } = options;
  let sql = 'SELECT * FROM leads WHERE 1=1';
  const params = {};

  if (query) {
    sql += ' AND (company LIKE @query OR email LIKE @query OR description LIKE @query)';
    params.query = `%${query}%`;
  }
  if (industry) {
    sql += ' AND industry LIKE @industry';
    params.industry = `%${industry}%`;
  }
  if (location) {
    sql += ' AND (city LIKE @location OR state LIKE @location OR country LIKE @location)';
    params.location = `%${location}%`;
  }

  const countSql = sql.replace('SELECT *', 'SELECT COUNT(*) as total');
  const total = getDb().prepare(countSql).get(params).total;

  sql += ` ORDER BY score DESC, created_at DESC LIMIT @limit OFFSET @offset`;
  params.limit = limit;
  params.offset = offset;

  const leads = getDb().prepare(sql).all(params);
  return { leads, total };
}

function getStats() {
  return getDb().prepare(`
    SELECT 
      (SELECT COUNT(*) FROM leads) as total_leads,
      (SELECT COUNT(*) FROM campaigns) as total_campaigns,
      (SELECT COUNT(*) FROM leads WHERE email IS NOT NULL AND email != '') as emails_found,
      (SELECT balance FROM credits LIMIT 1) as balance
  `).get();
}

function createCampaign(name, industry, location) {
  return getDb().prepare(`
    INSERT INTO campaigns (name, industry, location) VALUES (?, ?, ?)
  `).run(name, industry, location);
}

function getCampaigns() {
  return getDb().prepare('SELECT * FROM campaigns ORDER BY created_at DESC').all();
}

function getLeadsByCampaign(campaignId) {
  return getDb().prepare(`
    SELECT * FROM scraped_data WHERE campaign_id = ? ORDER BY created_at DESC
  `).all(campaignId);
}

function updateCredits(amount) {
  return getDb().prepare(`
    UPDATE credits SET balance = balance + ?, total_spent = total_spent + ?, last_updated = CURRENT_TIMESTAMP
  `).run(amount, Math.abs(amount));
}

module.exports = { init, getDb, insertLead, searchLeads, getStats, createCampaign, getCampaigns, getLeadsByCampaign, updateCredits };
