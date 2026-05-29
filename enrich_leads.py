#!/usr/bin/env python3
"""
Quick Lead Enrichment Engine
Finds websites and emails for BBB leads using Google search
"""
import urllib.request, urllib.parse, urllib.error
import csv, re, json, time, random, os, ssl
from datetime import datetime

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36',
]

def google_search(query):
    """Search Google and return result links"""
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=5"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        resp = urllib.request.urlopen(req, timeout=8, context=ssl_ctx)
        html = resp.read().decode('utf-8', errors='replace')
        links = re.findall(r'href="(https?://[^"]+)"', html)
        # Filter out google domains
        real_links = [l for l in links if 'google.com' not in l and 'gstatic.com' not in l]
        return real_links[:3]
    except:
        return []

def extract_email_from_website(url, timeout=5):
    """Try to find email on a company website"""
    try:
        req = urllib.request.Request(url, headers={
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        resp = urllib.request.urlopen(req, timeout=timeout, context=ssl_ctx)
        html = resp.read().decode('utf-8', errors='replace')
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)
        # Filter out common non-business emails
        biz_emails = [e for e in emails if not any(x in e.lower() for x in ['example.com', 'domain.com', 'yoursite.com'])]
        if biz_emails:
            return biz_emails[0]
    except:
        pass
    return ''

def enrich_lead(company, location):
    """Enrich a single lead with website and email"""
    # Search for company website
    search_query = f"{company} {location} official website"
    links = google_search(search_query)
    
    website = ''
    email = ''
    
    for link in links:
        if not any(dom in link for dom in ['facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'yelp.com', 'bbb.org']):
            # Clean URL
            link = link.split('&')[0].split('?')[0]
            if link.startswith('/url?q='):
                link = link.replace('/url?q=', '')
            if not website:
                website = link
            # Try to find email
            if not email:
                email = extract_email_from_website(link)
            if website and email:
                break
    
    return website, email

def enrich_all_leads(input_file, output_file, max_leads=500):
    """Enrich all leads with websites and emails"""
    leads = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            leads.append(row)
    
    print(f"Loaded {len(leads)} leads from {input_file}")
    print(f"Enriching up to {max_leads} leads...")
    
    enriched = 0
    for i, lead in enumerate(leads[:max_leads]):
        company = lead.get('company', '')
        if not company:
            continue
        
        # Skip if already has website
        if lead.get('website', '').strip():
            continue
        
        location = f"{lead.get('city', '')} {lead.get('state', '')} {lead.get('location', '')}".strip()
        if not location:
            location = lead.get('location', '')
        
        sys.stdout.write(f"\r  [{i+1}/{min(max_leads, len(leads))}] {company[:30]:30s}... ")
        sys.stdout.flush()
        
        try:
            website, email = enrich_lead(company, location)
            if website:
                lead['website'] = website
                enriched += 1
            if email:
                lead['email'] = email
            
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            pass
    
    print(f"\n✅ Enriched {enriched} leads with websites/emails")
    
    # Save enriched file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        if leads:
            writer = csv.DictWriter(f, fieldnames=leads[0].keys())
            writer.writeheader()
            writer.writerows(leads)
    
    print(f"✅ Saved to {output_file}")
    return leads

if __name__ == '__main__':
    import sys
    
    input_file = sys.argv[1] if len(sys.argv) > 1 else '/data/app/data/exports/test_plumber.csv'
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.csv', '_enriched.csv')
    max_leads = int(sys.argv[3]) if len(sys.argv) > 3 else 500
    
    enrich_all_leads(input_file, output_file, max_leads)
