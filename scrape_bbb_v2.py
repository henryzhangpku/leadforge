#!/usr/bin/env python3
"""
BBB Business Scraper v2 - Professional Lead Generation
Extracts verified business data from Better Business Bureau
"""
import urllib.request, urllib.error, urllib.parse
import json, csv, re, time, random, os, ssl, sys
from datetime import datetime
from bs4 import BeautifulSoup

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
]

def fetch(url, timeout=15):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.bbb.org/',
            })
            resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
            return resp.read().decode('utf-8', errors='replace')
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep((attempt+1)*5)
                continue
            raise
        except Exception as e:
            if attempt < 2:
                time.sleep(2)
                continue
            raise

def scrape_bbb_search(industry, location, max_pages=5):
    """Scrape BBB search results for businesses"""
    all_businesses = []
    
    print(f"\n{'='*60}")
    print(f"📊 Scraping: {industry} in {location}")
    
    for page in range(1, max_pages + 1):
        params = urllib.parse.urlencode({
            'find_text': industry,
            'find_loc': location,
            'page': page
        })
        url = f"https://www.bbb.org/search?{params}"
        
        sys.stdout.write(f"  Page {page}... ")
        sys.stdout.flush()
        
        try:
            html = fetch(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            # Find all result cards
            cards = soup.find_all('div', class_='result-card')
            
            if not cards:
                # Try alternative selector
                cards = soup.select('.card.result-card')
            
            if not cards:
                print("No cards found")
                break
            
            print(f"{len(cards)} businesses")
            
            for card in cards:
                biz = extract_business(card, industry, location)
                if biz and biz['company']:
                    all_businesses.append(biz)
            
            time.sleep(random.uniform(1.5, 3.0))
            
        except Exception as e:
            print(f"Error: {str(e)[:80]}")
            break
    
    return all_businesses

def extract_business(card, industry, location):
    """Extract business data from a BBB result card"""
    biz = {
        'company': '',
        'website': '',
        'phone': '',
        'address': '',
        'city': '',
        'state': '',
        'zip': '',
        'email': '',
        'description': '',
        'categories': '',
        'rating': '',
        'bbb_link': '',
        'industry': industry,
        'location': location,
        'source': 'bbb.org',
        'accredited': False,
    }
    
    # Business name
    name_elem = card.find('h3', class_='result-business-name')
    if not name_elem:
        name_elem = card.find(class_='result-business-name')
    if name_elem:
        a_tag = name_elem.find('a')
        if a_tag:
            biz['company'] = a_tag.get_text(strip=True)
            href = a_tag.get('href', '')
            if href:
                biz['bbb_link'] = 'https://www.bbb.org' + href if href.startswith('/') else href
    
    # Categories / description
    p_tag = card.find('p', class_='bds-body')
    if p_tag:
        biz['categories'] = p_tag.get_text(strip=True)
    
    # Rating
    rating_details = card.find('details', class_='result-rating-details')
    if rating_details:
        summary = rating_details.find('summary')
        if summary:
            rating_text = summary.get_text(strip=True)
            if ':' in rating_text:
                biz['rating'] = rating_text.split(':')[1].strip()
            else:
                biz['rating'] = rating_text
    
    # Check for accredited seal
    seal = card.find('img', src=lambda x: x and 'Accredited' in x)
    biz['accredited'] = seal is not None
    
    # Phone - look for phone patterns in the card text
    card_text = card.get_text()
    phone_match = re.search(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', card_text)
    if phone_match:
        biz['phone'] = phone_match.group()
    
    # Email
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', card_text)
    if email_match:
        biz['email'] = email_match.group()
    
    # Try to get more details from the profile link
    # (We'll do this in a separate enrichment pass)
    
    # Also check for address info in the card
    address_elem = card.find(string=re.compile(r'\d+\s+[A-Za-z]'))
    if address_elem:
        addr_text = address_elem.strip()
        if len(addr_text) > 10 and any(c.isdigit() for c in addr_text):
            biz['address'] = addr_text
    
    return biz

def scrape_bbb_profile(profile_url):
    """Scrape a BBB business profile page for enriched data"""
    try:
        html = fetch(profile_url, timeout=10)
        soup = BeautifulSoup(html, 'html.parser')
        
        data = {}
        
        # Phone
        phone_elem = soup.find('a', href=lambda x: x and x.startswith('tel:'))
        if phone_elem:
            data['phone'] = phone_elem.get_text(strip=True)
        
        # Website
        website_elem = soup.find('a', href=lambda x: x and ('http' in x) and not 'bbb.org' in x)
        if website_elem:
            data['website'] = website_elem.get('href', '')
        
        # Address
        addr_elem = soup.find(class_=re.compile(r'address', re.I))
        if addr_elem:
            data['address'] = addr_elem.get_text(strip=True)
        
        # Try to find structured business info sections
        # Look for contact info in the profile
        contact_section = soup.find(string=re.compile(r'Contact', re.I))
        if contact_section:
            parent = contact_section.find_parent(['div', 'section'])
            if parent:
                data['contact_text'] = parent.get_text(strip=True)[:500]
        
        return data
    except:
        return {}

def save_businesses(businesses, filename):
    """Save businesses to CSV"""
    if not businesses:
        print("No businesses to save!")
        return
    
    fieldnames = ['company', 'website', 'phone', 'address', 'city', 'state', 'zip',
                  'email', 'description', 'categories', 'rating', 'industry', 
                  'location', 'source', 'accredited', 'bbb_link']
    
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for biz in businesses:
            row = {k: biz.get(k, '') for k in fieldnames}
            writer.writerow(row)
    
    print(f"✅ Saved {len(businesses)} to {filename}")

def run_campaigns():
    """Run all scraping campaigns"""
    output_dir = '/data/app/data/exports'
    os.makedirs(output_dir, exist_ok=True)
    
    all_businesses = []
    
    # Campaigns: (industry, location, pages)
    campaigns = [
        ("Plumber", "Chicago, IL", 3),
        ("Electrician", "New York, NY", 3),
        ("Dentist", "Los Angeles, CA", 3),
        ("Real Estate Agent", "Houston, TX", 3),
        ("Restaurant", "San Francisco, CA", 3),
        ("General Contractor", "Miami, FL", 3),
        ("Lawyer", "Boston, MA", 3),
        ("Physician", "Seattle, WA", 3),
        ("Accountant", "Denver, CO", 3),
        ("Insurance Agent", "Phoenix, AZ", 3),
        ("Auto Repair", "Dallas, TX", 3),
        ("Landscaper", "Atlanta, GA", 3),
        ("Painter", "Portland, OR", 3),
        ("HVAC Contractor", "Minneapolis, MN", 3),
        ("Roofer", "Charlotte, NC", 3),
        ("Web Designer", "Austin, TX", 3),
        ("Marketing Agency", "Nashville, TN", 3),
        ("Cleaning Service", "Orlando, FL", 3),
        ("IT Support", "San Diego, CA", 3),
        ("Photographer", "Philadelphia, PA", 3),
    ]
    
    for industry, location, pages in campaigns:
        try:
            biz_list = scrape_bbb_search(industry, location, max_pages=pages)
            all_businesses.extend(biz_list)
            
            # Save individual file
            safe_name = f"{industry.replace(' ', '_')}_{location.split(',')[0].strip()}"
            filepath = os.path.join(output_dir, f"bbb_{safe_name}.csv")
            save_businesses(biz_list, filepath)
            
            time.sleep(random.uniform(2.0, 4.0))
        except Exception as e:
            print(f"❌ Failed {industry}/{location}: {str(e)[:80]}")
    
    # Save master file
    master_file = os.path.join(output_dir, "BBB_Master_Lead_List.csv")
    save_businesses(all_businesses, master_file)
    
    print(f"\n{'='*60}")
    print(f"🎯 COMPLETE: {len(all_businesses)} total businesses")
    print(f"📁 Master: {master_file}")
    print(f"{'='*60}")
    
    # Stats
    cats = {}
    for b in all_businesses:
        ind = b.get('industry', 'Unknown')
        cats[ind] = cats.get(ind, 0) + 1
    
    print("\n📊 Breakdown:")
    for ind, count in sorted(cats.items()):
        print(f"  {ind}: {count}")
    
    return all_businesses

if __name__ == '__main__':
    print("🏢 BBB Lead Scraper v2")
    print(f"⏰ {datetime.now().isoformat()}")
    all_biz = run_campaigns()
    print(f"\n✅ Done: {datetime.now().isoformat()}")
