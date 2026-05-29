#!/usr/bin/env python3
"""Update Gumroad product with file and publish it"""
import json, http.client, urllib.parse

TOKEN = 'W8g5HusENmFE4oXsF9Ras5Mwg2CU-jg_GbAXT1xkRNo'
FILE_URL = 'https://s3.amazonaws.com/gumroad/attachments/7353874962464/a2e44ba2dcd6e9d17affe73bb2ce8fd6/original/BBB_Premium_Lead_Database.csv'
PRODUCT_ID = 'VIgvYoW-RmUxcQ6V6FZMPQ=='

conn = http.client.HTTPSConnection('api.gumroad.com')
pid = urllib.parse.quote(PRODUCT_ID, safe='')

params = {
    'access_token': TOKEN,
    'name': 'BBB Verified Business Leads - Complete Database (747 Leads, 20 Industries)',
    'price': '29900',
    'description': '747 verified business leads from Better Business Bureau (BBB) across 20 US cities and industries.\n\nINCLUDES: Phone numbers, BBB ratings, accreditation status, business categories, BBB profile links.\n\nINDUSTRIES: Plumbers, Electricians, Dentists, Real Estate, Restaurants, Contractors, Lawyers, Physicians, Accountants, Insurance, Auto Repair, Landscapers, Painters, HVAC, Roofers, Web Design, Marketing, Cleaning, IT, Photography\n\nFormat: CSV (Excel, Google Sheets, CRM compatible)',
    'published': 'true',
    'files[][url]': FILE_URL,
    'files[][name]': 'BBB_Premium_Lead_Database.csv',
}

body = urllib.parse.urlencode(params)
conn.request('PUT', f'/v2/products/{pid}', body=body.encode(),
             headers={'Content-Type': 'application/x-www-form-urlencoded'})
raw = conn.getresponse().read().decode()
conn.close()

result = json.loads(raw) if raw else {}
print(f'Success: {result.get("success")}')
if result.get('success'):
    p = result.get('product', {})
    print(f'Name: {p.get("name")}')
    print(f'Files: {len(p.get("files", []))}')
    for f in p.get('files', []):
        print(f'  - {f.get("name", "?")} ({f.get("size", "?")} bytes)')
    print(f'Published: {p.get("published")}')
    print(f'Price: ${float(p.get("price", 0))/100:.0f}')
    print(f'URL: https://henryzhangdigital.gumroad.com/l/ceoxf')
else:
    print(f'Error: {result.get("message", raw[:200])}')
