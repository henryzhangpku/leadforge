const express = require('express');
const router = express.Router();
const db = require('../db');
const scraper = require('../scraper');

// GET /api/stats
router.get('/stats', (req, res) => {
  try {
    const stats = db.getStats();
    res.json(stats);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/leads
router.get('/leads', (req, res) => {
  try {
    const result = db.searchLeads({
      query: req.query.q,
      industry: req.query.industry,
      location: req.query.location,
      limit: parseInt(req.query.limit || '100'),
      offset: parseInt(req.query.offset || '0'),
    });
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/leads/export
router.get('/leads/export', (req, res) => {
  try {
    const format = req.query.format || 'json';
    const result = db.searchLeads({
      query: req.query.q,
      industry: req.query.industry,
      location: req.query.location,
      limit: parseInt(req.query.limit || '10000'),
      offset: 0,
    });

    if (format === 'csv') {
      const headers = ['company','website','email','phone','address','city','state','country','industry','description','source'];
      let csv = headers.join(',') + '\n';
      for (const lead of result.leads) {
        const row = headers.map(h => {
          const val = (lead[h] || '').toString().replace(/"/g, '""');
          return `"${val}"`;
        });
        csv += row.join(',') + '\n';
      }
      res.setHeader('Content-Type', 'text/csv');
      res.setHeader('Content-Disposition', `attachment; filename=leads-${Date.now()}.csv`);
      return res.send(csv);
    }
    
    res.json(result.leads);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/scrape - Start a scrape campaign
router.post('/scrape', async (req, res) => {
  try {
    const { industry, location, campaign_name } = req.body;
    if (!industry || !location) {
      return res.status(400).json({ error: 'industry and location are required' });
    }

    const name = campaign_name || `${industry} - ${location}`;
    const campaign = db.createCampaign(name, industry, location);
    
    // Respond immediately, scrape in background
    res.json({ 
      success: true, 
      message: 'Scrape started',
      campaign_id: campaign.lastInsertRowid,
      note: 'Scraping is running in the background. Check /leads for results.'
    });

    // Background scrape
    try {
      const leads = await scraper.scrapeAll(industry, location);
      db.getDb().prepare('UPDATE campaigns SET scraped_leads = ?, status = ? WHERE id = ?')
        .run(leads.length, 'completed', campaign.lastInsertRowid);
      console.log(`✅ Campaign #${campaign.lastInsertRowid}: ${leads.length} leads scraped`);
    } catch (err) {
      db.getDb().prepare('UPDATE campaigns SET status = ? WHERE id = ?')
        .run('failed', campaign.lastInsertRowid);
      console.error(`❌ Campaign #${campaign.lastInsertRowid} failed: ${err.message}`);
    }
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/campaigns
router.get('/campaigns', (req, res) => {
  try {
    res.json(db.getCampaigns());
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/credits/add - Add credit balance (admin)
router.post('/credits/add', (req, res) => {
  try {
    const { amount } = req.body;
    if (!amount || amount <= 0) return res.status(400).json({ error: 'Invalid amount' });
    db.updateCredits(amount);
    res.json({ success: true, balance: db.getStats().balance });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/industries - List available industries already in DB
router.get('/industries', (req, res) => {
  try {
    const industries = db.getDb().prepare('SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND industry != "" ORDER BY industry').all();
    res.json(industries.map(i => i.industry));
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/quick-leads/:industry/:location
router.get('/quick-leads/:industry/:location', async (req, res) => {
  try {
    const { industry, location } = req.params;
    res.json({ status: 'started', message: `Scraping ${industry} leads in ${location}...` });
    
    const leads = await scraper.scrapeAll(industry, location);
    console.log(`Quick scrape: ${leads.length} ${industry} leads from ${location}`);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;
