#!/usr/bin/env python3
"""
Professional BBB Business Scraper
Scrapes Better Business Bureau for verified business listings
Outputs clean CSV data ready for sale
"""
import urllib.request, urllib.error, urllib.parse
import json, csv, re, time, random, os, ssl, sys
from datetime import datetime

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
]

def get_headers():
    return {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': 'https://www.bbb.org/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

def fetch_url(url, timeout=15):
    """Fetch a URL with retry logic"""
    for attempt in range(3):
        try:
            headers = get_headers()
            req = urllib.request.Request(url, headers=headers)
            resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
            raw = resp.read()
            # Try to decode
            try:
                return raw.decode('utf-8', errors='replace')
            except:
                return raw.decode('iso-8859-1', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = (attempt + 1) * 5
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
                continue
            elif e.code == 403:
                print(f"  Blocked (403), rotating IP...")
                time.sleep(3)
                continue
            raise
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            raise

def extract_businesses_from_html(html, industry, location):
    """Parse BBB search results page for business listings"""
    businesses = []
    
    # Try to find JSON-LD structured data first
    import html as html_mod
    
    # Pattern: business cards in BBB results
    # Each business is in a search-result-item or similar container
    
    # Extract from script tags with JSON-LD
    json_pattern = r'<script type="application/ld\+json">(.*?)</script>'
    json_matches = re.findall(json_pattern, html, re.DOTALL)
    
    for json_str in json_matches:
        try:
            data = json.loads(json_str)
            if isinstance(data, dict) and data.get('@type') in ['LocalBusiness', 'Organization', 'Business']:
                biz = {
                    'company': data.get('name', ''),
                    'website': data.get('url', ''),
                    'phone': data.get('telephone', ''),
                    'address': '',
                    'city': '',
                    'state': '',
                    'zip': '',
                    'description': data.get('description', ''),
                    'email': '',
                    'industry': industry,
                    'location': location,
                    'source': 'bbb.org',
                    'rating': data.get('aggregateRating', {}).get('ratingValue', '') if isinstance(data.get('aggregateRating'), dict) else '',
                }
                addr = data.get('address', {})
                if isinstance(addr, dict):
                    biz['address'] = f"{addr.get('streetAddress', '')}, {addr.get('addressLocality', '')}, {addr.get('addressRegion', '')} {addr.get('postalCode', '')}".strip(', ')
                    biz['city'] = addr.get('addressLocality', '')
                    biz['state'] = addr.get('addressRegion', '')
                    biz['zip'] = addr.get('postalCode', '')
                elif isinstance(addr, str):
                    biz['address'] = addr
                if biz['company']:
                    businesses.append(biz)
        except:
            pass
    
    # If no JSON-LD found, try regex patterns on the HTML
    if not businesses:
        # Look for business names in h3/h2 tags
        biz_blocks = re.findall(
            r'<h3[^>]*class="[^"]*business-name[^"]*"[^>]*>(.*?)</h3>',
            html, re.DOTALL
        )
        
        phones = re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)
        websites = re.findall(r'href="(https?://[^"]+)"[^>]*>Website</a>', html)
        
        for i, name_html in enumerate(biz_blocks):
            name = re.sub(r'<[^>]+>', '', name_html).strip()
            if name and len(name) > 2:
                biz = {
                    'company': name,
                    'website': websites[i] if i < len(websites) else '',
                    'phone': phones[i] if i < len(phones) else '',
                    'address': '',
                    'city': '',
                    'state': '',
                    'zip': '',
                    'description': '',
                    'email': '',
                    'industry': industry,
                    'location': location,
                    'source': 'bbb.org',
                    'rating': '',
                }
                businesses.append(biz)
    
    return businesses

def scrape_industry(industry, location, max_pages=5):
    """Scrape BBB for a specific industry and location"""
    all_businesses = []
    base_query = urllib.parse.quote(f"{industry} {location}")
    
    print(f"\n{'='*60}")
    print(f"Scraping: {industry} in {location}")
    print(f"{'='*60}")
    
    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"https://www.bbb.org/search?find_text={urllib.parse.quote(industry)}&find_loc={urllib.parse.quote(location)}"
        else:
            url = f"https://www.bbb.org/search?page={page}&find_text={urllib.parse.quote(industry)}&find_loc={urllib.parse.quote(location)}"
        
        print(f"  Page {page}...", end=' ', flush=True)
        
        try:
            html = fetch_url(url)
            if not html or len(html) < 500:
                print("Empty response")
                break
            
            businesses = extract_businesses_from_html(html, industry, location)
            print(f"Found {len(businesses)} businesses")
            
            if not businesses:
                print("  No more results")
                break
            
            all_businesses.extend(businesses)
            
            # Polite delay
            time.sleep(random.uniform(2.0, 4.0))
            
        except Exception as e:
            print(f"Error: {str(e)[:60]}")
            break
    
    return all_businesses

def save_to_csv(businesses, filename):
    """Save businesses to CSV"""
    if not businesses:
        print("No businesses to save!")
        return
    
    fieldnames = ['company', 'website', 'phone', 'address', 'city', 'state', 'zip', 
                  'email', 'description', 'industry', 'location', 'rating', 'source']
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for biz in businesses:
            row = {k: biz.get(k, '') for k in fieldnames}
            writer.writerow(row)
    
    print(f"\n✅ Saved {len(businesses)} businesses to {filename}")

def scrape_all():
    """Run all scraping campaigns"""
    campaigns = [
        # (Industry, Location, Pages)
        ("Plumber", "Chicago, IL", 3),
        ("Electrician", "New York, NY", 3),
        ("Dentist", "Los Angeles, CA", 3),
        ("Real Estate Agent", "Houston, TX", 3),
        ("Restaurant", "San Francisco, CA", 3),
        ("Contractor", "Miami, FL", 3),
        ("Lawyer", "Boston, MA", 3),
        ("Doctor", "Seattle, WA", 3),
        ("Accountant", "Denver, CO", 3),
        ("Insurance Agent", "Phoenix, AZ", 3),
        ("Auto Repair", "Dallas, TX", 3),
        ("Landscaper", "Atlanta, GA", 3),
        ("Painter", "Portland, OR", 3),
        ("HVAC Contractor", "Minneapolis, MN", 3),
        ("Roofing Contractor", "Charlotte, NC", 3),
    ]
    
    all_businesses = []
    output_dir = '/data/app/data/exports'
    os.makedirs(output_dir, exist_ok=True)
    
    for industry, location, pages in campaigns:
        try:
            biz_list = scrape_industry(industry, location, max_pages=pages)
            all_businesses.extend(biz_list)
            
            # Save individual industry file
            safe_name = f"{industry.replace(' ', '_')}_{location.split(',')[0].replace(' ', '_')}"
            filename = os.path.join(output_dir, f"bbb_{safe_name}.csv")
            save_to_csv(biz_list, filename)
            
            # Small delay between campaigns
            time.sleep(random.uniform(3.0, 5.0))
            
        except Exception as e:
            print(f"❌ Campaign failed ({industry}/{location}): {str(e)[:80]}")
    
    # Save master file
    master_file = os.path.join(output_dir, "bbb_all_leads_master.csv")
    save_to_csv(all_businesses, master_file)
    
    print(f"\n{'='*60}")
    print(f"✅ COMPLETE: {len(all_businesses)} total businesses scraped")
    print(f"📁 Master file: {master_file}")
    print(f"{'='*60}")
    
    return all_businesses

if __name__ == '__main__':
    print("BBB Professional Business Scraper v1.0")
    print(f"Started: {datetime.now().isoformat()}")
    
    all_biz = scrape_all()
    
    # Summary stats
    industries = {}
    for biz in all_biz:
        ind = biz.get('industry', 'Unknown')
        industries[ind] = industries.get(ind, 0) + 1
    
    print("\n📊 Summary by Industry:")
    for ind, count in sorted(industries.items()):
        print(f"  {ind}: {count}")
    
    print(f"\n🏁 Finished: {datetime.now().isoformat()}")
