const axios = require('axios');
const cheerio = require('cheerio');

const USER_AGENTS = [
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
];

function getRandomUA() {
  return USER_AGENTS[Math.floor(Math.random() * USER_AGENTS.length)];
}

async function fetchPage(url, timeout = 15000) {
  try {
    const resp = await axios.get(url, {
      headers: { 
        'User-Agent': getRandomUA(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
      },
      timeout,
      maxRedirects: 5,
    });
    return resp.data;
  } catch (err) {
    throw new Error(`Failed to fetch ${url}: ${err.message}`);
  }
}

// Scrape Yellow Pages style business directories
async function scrapeYellowPages(industry, location, maxPages = 3) {
  const leads = [];
  const baseUrl = `https://www.yellowpages.com/search?search_terms=${encodeURIComponent(industry)}&geo_location_terms=${encodeURIComponent(location)}`;

  for (let page = 1; page <= maxPages; page++) {
    try {
      const url = page === 1 ? baseUrl : `${baseUrl}&page=${page}`;
      console.log(`Scraping YP page ${page}: ${url}`);
      const html = await fetchPage(url);
      const $ = cheerio.load(html);

      $('.result').each((i, el) => {
        const name = $(el).find('.business-name').text().trim();
        if (!name) return;

        const phone = $(el).find('.phone').text().trim();
        const website = $(el).find('.tracked-visit-link').attr('href') || '';
        const address = $(el).find('.street-address').text().trim();
        const cityState = $(el).find('.locality').text().trim();
        const email = extractEmail($(el).html() || '');
        
        // Parse address
        let city = '', state = '', country = 'US';
        if (cityState) {
          const parts = cityState.split(',').map(s => s.trim());
          city = parts[0] || '';
          state = parts[1] || '';
        }

        leads.push({
          company: name,
          website: website.startsWith('http') ? website : '',
          email,
          phone,
          address,
          city,
          state,
          country,
          industry,
          source: 'yellowpages',
          score: 50,
          description: $(el).find('.snippet').text().trim(),
        });
      });

      // Check if there's a next page
      if ($('.pagination .next').length === 0) break;
      // Small delay to be polite
      await new Promise(r => setTimeout(r, 1000));
    } catch (err) {
      console.error(`Error on YP page ${page}: ${err.message}`);
      break;
    }
  }

  return leads;
}

// Scrape Manta business directory
async function scrapeManta(industry, location, maxPages = 3) {
  const leads = [];
  const baseUrl = `https://www.manta.com/search?search=${encodeURIComponent(industry)}&location=${encodeURIComponent(location)}`;

  for (let page = 1; page <= maxPages; page++) {
    try {
      const url = page === 1 ? baseUrl : `${baseUrl}&offset=${(page-1)*20}`;
      console.log(`Scraping Manta page ${page}`);
      const html = await fetchPage(url);
      const $ = cheerio.load(html);

      $('.search-result-item').each((i, el) => {
        const name = $(el).find('.company-name').text().trim();
        if (!name) return;

        leads.push({
          company: name,
          website: $(el).find('.company-website a').attr('href') || '',
          phone: $(el).find('.phone').text().trim(),
          address: $(el).find('.address').text().trim(),
          city: $(el).find('.city').text().trim(),
          state: $(el).find('.state').text().trim(),
          country: 'US',
          industry,
          source: 'manta',
          score: 40,
          description: $(el).find('.description').text().trim(),
        });
      });

      await new Promise(r => setTimeout(r, 1500));
    } catch (err) {
      console.error(`Error on Manta page ${page}: ${err.message}`);
      break;
    }
  }
  return leads;
}

// Scrape Crunchbase (limited - public pages)
async function scrapeCrunchbase(industry, maxPages = 2) {
  const leads = [];
  // Using Crunchbase's public API-like query
  const query = encodeURIComponent(industry);
  
  for (let page = 1; page <= maxPages; page++) {
    try {
      const url = `https://www.crunchbase.com/discover/organization.companies?q=${query}&page=${page}`;
      console.log(`Scraping CB page ${page}`);
      const html = await fetchPage(url);
      const $ = cheerio.load(html);
      
      $('grid-cell').each((i, el) => {
        const name = $(el).find('.identifier-label').text().trim();
        if (!name) return;
        
        leads.push({
          company: name,
          website: $(el).find('a[href*="http"]').attr('href') || '',
          description: $(el).find('.short_description').text().trim(),
          industry,
          source: 'crunchbase',
          score: 70,
          country: 'US',
        });
      });
      await new Promise(r => setTimeout(r, 2000));
    } catch (err) {
      console.error(`Error on CB page: ${err.message}`);
      break;
    }
  }
  return leads;
}

// Extract emails from text
function extractEmail(text) {
  const match = text.match(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/);
  return match ? match[0] : '';
}

// Extract phone from text  
function extractPhone(text) {
  const match = text.match(/\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}/);
  return match ? match[0] : '';
}

// Google Maps scraper (basic)
async function scrapeGoogleMaps(query, location, maxResults = 50) {
  const leads = [];
  // We'll use textise dot iitty to get Google Maps data
  // This is a simplified approach
  console.log(`Google Maps search for "${query}" in "${location}"`);
  
  // For now, we'll use multiple directory sources instead
  return leads;
}

// Scrape Indeed company pages
async function scrapeIndeedCompanies(industry, location, maxPages = 2) {
  const leads = [];
  try {
    const searchQuery = `${industry} companies ${location}`;
    const url = `https://www.indeed.com/cmp?q=${encodeURIComponent(searchQuery)}`;
    console.log(`Scraping Indeed companies: ${url}`);
    const html = await fetchPage(url);
    const $ = cheerio.load(html);

    $('.cmp-card-container').each((i, el) => {
      const name = $(el).find('.cmp-card-name').text().trim();
      if (!name) return;
      
      leads.push({
        company: name,
        description: $(el).find('.cmp-card-description').text().trim(),
        website: $(el).find('a[href*="http"]').attr('href') || '',
        industry,
        source: 'indeed',
        score: 45,
        country: 'US',
      });
    });
  } catch (err) {
    console.error(`Indeed scrape error: ${err.message}`);
  }
  return leads;
}

// Main scrape function that runs all sources
async function scrapeAll(industry, location) {
  const db = require('./db');
  const results = [];

  // Run scrapers in parallel
  const scrapers = [
    scrapeYellowPages(industry, location, 5),
    scrapeManta(industry, location, 3),
    scrapeIndeedCompanies(industry, location, 2),
  ];

  const scrapedResults = await Promise.allSettled(scrapers);
  
  for (const result of scrapedResults) {
    if (result.status === 'fulfilled' && result.value.length > 0) {
      for (const lead of result.value) {
        try {
          db.insertLead(lead);
          results.push(lead);
        } catch (err) {
          // Skip duplicates
        }
      }
    }
  }

  // Also scrape specific top companies in this industry
  const enrichedLeads = results.slice(0, 20);
  for (const lead of enrichedLeads) {
    if (lead.website) {
      try {
        const html = await fetchPage(lead.website, 8000);
        const $ = cheerio.load(html);
        
        // Find contact page
        const contactLink = $('a[href*="contact"]').first().attr('href');
        if (contactLink) {
          const contactUrl = contactLink.startsWith('http') ? contactLink : new URL(contactLink, lead.website).href;
          try {
            const contactHtml = await fetchPage(contactUrl, 8000);
            const email = extractEmail(contactHtml);
            if (email && !lead.email) {
              lead.email = email;
              db.getDb().prepare('UPDATE leads SET email = ? WHERE company = ? AND source = ?').run(email, lead.company, lead.source);
            }
          } catch {}
        }
        
        // Extract social links
        const socialLinks = [];
        $('a[href*="linkedin.com"], a[href*="twitter.com"], a[href*="facebook.com"]').each((i, el) => {
          socialLinks.push($(el).attr('href'));
        });
        if (socialLinks.length > 0) {
          lead.social_links = socialLinks.join(', ');
        }
        
        await new Promise(r => setTimeout(r, 1000));
      } catch {}
    }
  }

  return results;
}

module.exports = { scrapeAll, scrapeYellowPages, scrapeManta, scrapeCrunchbase, scrapeIndeedCompanies, fetchPage, extractEmail, extractPhone };
