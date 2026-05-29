const express = require('express');
const router = express.Router();
const db = require('../db');

// Home page - Dashboard
router.get('/', (req, res) => {
  const stats = db.getStats();
  res.render('dashboard', { 
    title: 'LeadForge - Business Intelligence',
    stats
  });
});

// Leads page
router.get('/leads', (req, res) => {
  const result = db.searchLeads({
    query: req.query.q,
    industry: req.query.industry,
    location: req.query.location,
    limit: 500,
    offset: 0,
  });
  
  const industries = db.getDb().prepare('SELECT DISTINCT industry FROM leads WHERE industry IS NOT NULL AND industry != "" ORDER BY industry').all().map(i => i.industry);
  
  res.render('leads', {
    title: 'Leads Database',
    leads: result.leads,
    total: result.total,
    industries,
    query: req.query.q || '',
    industry: req.query.industry || '',
    location: req.query.location || '',
  });
});

// Scrape page
router.get('/scrape', (req, res) => {
  res.render('scrape', { title: 'Scrape Leads' });
});

// Campaigns page
router.get('/campaigns', (req, res) => {
  const campaigns = db.getCampaigns();
  res.render('campaigns', { title: 'Campaigns', campaigns });
});

// Pricing page
router.get('/pricing', (req, res) => {
  res.render('pricing', { title: 'Pricing' });
});

module.exports = router;
