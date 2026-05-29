#!/usr/bin/env python3
"""
Gumroad Product Uploader
Uploads BBB lead data as Gumroad products
"""
import json, os, sys, http.client, urllib.request, urllib.parse
from hashlib import md5

TOKEN = 'W8g5HusENmFE4oXsF9Ras5Mwg2CU-jg_GbAXT1xkRNo'
GUMROAD = 'api.gumroad.com'

def gumroad_get(endpoint):
    conn = http.client.HTTPSConnection(GUMROAD)
    conn.request('GET', f'/v2/{endpoint}?access_token={TOKEN}')
    resp = conn.getresponse()
    data = json.loads(resp.read().decode())
    conn.close()
    return data

def gumroad_post(endpoint, fields, files=None):
    conn = http.client.HTTPSConnection(GUMROAD)
    boundary = '----Boundary7MA4YW'
    body = []
    
    for key, val in fields.items():
        body.append(f'--{boundary}'.encode())
        body.append(f'Content-Disposition: form-data; name="{key}"'.encode())
        body.append(b'')
        body.append(str(val).encode())
    
    if files:
        for file_key, file_path in files:
            body.append(f'--{boundary}'.encode())
            fname = os.path.basename(file_path)
            body.append(f'Content-Disposition: form-data; name="{file_key}"; filename="{fname}"'.encode())
            body.append(b'Content-Type: application/octet-stream')
            body.append(b'')
            with open(file_path, 'rb') as f:
                body.append(f.read())
    
    body.append(f'--{boundary}--'.encode())
    body.append(b'')
    body_data = b'\r\n'.join(body)
    
    conn.request('POST', f'/v2/{endpoint}', body=body_data,
                 headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
    resp = conn.getresponse()
    result = json.loads(resp.read().decode())
    conn.close()
    return result

def gumroad_put(endpoint, fields):
    conn = http.client.HTTPSConnection(GUMROAD)
    body = urllib.parse.urlencode(fields).encode()
    conn.request('PUT', f'/v2/{endpoint}', body=body,
                 headers={'Content-Type': 'application/x-www-form-urlencoded'})
    resp = conn.getresponse()
    data = resp.read().decode()
    conn.close()
    if data:
        return json.loads(data)
    return {'success': False, 'message': 'Empty response'}

def presign_file(filepath):
    """Step 1: Get presigned URL for file upload"""
    print(f'  Presigning: {os.path.basename(filepath)}...', end=' ')
    with open(filepath, 'rb') as f:
        content = f.read()
    content_md5 = md5(content).hexdigest()
    filesize = len(content)
    filename = os.path.basename(filepath)
    
    result = gumroad_post('files/presign', {
        'access_token': TOKEN,
        'filename': filename,
        'filesize': filesize,
        'content_md5': content_md5,
    })
    
    if result.get('success'):
        print('✅')
        return result, content
    else:
        print(f'❌ {result.get("message", "unknown error")}')
        return None, None

def upload_to_s3(presign_data, file_content):
    """Step 2: Upload file parts to S3"""
    print(f'  Uploading to S3...', end=' ')
    upload_urls = presign_data.get('upload_urls', [])
    file_uid = presign_data.get('file_uid', '')
    
    if not upload_urls:
        print('❌ No upload URLs')
        return False
    
    part_size = presign_data.get('part_size', len(file_content))
    
    for i, url_info in enumerate(upload_urls):
        url = url_info.get('url', '')
        part_number = url_info.get('part_number', i + 1)
        
        start = (part_number - 1) * part_size
        end = min(start + part_size, len(file_content))
        part_data = file_content[start:end]
        
        req = urllib.request.Request(url, data=part_data, method='PUT')
        req.add_header('Content-Type', 'application/octet-stream')
        urllib.request.urlopen(req, timeout=60)
    
    print('✅')
    return True

def complete_upload(file_uid):
    """Step 3: Complete the upload"""
    print(f'  Completing upload...', end=' ')
    result = gumroad_post('files/complete', {
        'access_token': TOKEN,
        'file_uid': file_uid,
    })
    if result.get('success'):
        print('✅')
        return result.get('file', {})
    else:
        print(f'❌ {result.get("message", "error")}')
        return None

def create_product(name, price_cents, desc, file_urls=None):
    """Create product with optional file attachments"""
    fields = {
        'access_token': TOKEN,
        'name': name,
        'price': price_cents,
        'description': desc,
    }
    
    if file_urls:
        for i, url in enumerate(file_urls):
            fields[f'files[][url]'] = url
    
    result = gumroad_post('products', fields)
    return result

def update_product(product_id, file_urls):
    """Update product with file attachments"""
    fields = {
        'access_token': TOKEN,
    }
    for i, url in enumerate(file_urls):
        fields[f'files[][url]'] = url
    
    result = gumroad_put(f'products/{product_id}', fields)
    return result

def upload_file_to_gumroad(filepath):
    """Full flow: presign → upload → complete"""
    presign, content = presign_file(filepath)
    if not presign:
        return None
    
    file_uid = presign.get('file_uid', '')
    if not upload_to_s3(presign, content):
        return None
    
    file_info = complete_upload(file_uid)
    return file_info

def main():
    print('='*60)
    print('GUMROAD PRODUCT UPLOADER')
    print('='*60)
    
    # Upload CSV file
    csv_path = '/data/app/data/packages/BBB_Premium_Lead_Database.csv'
    json_path = '/data/app/data/packages/BBB_Premium_Lead_Database.json'
    
    print('\n📤 Uploading CSV file...')
    csv_file = upload_file_to_gumroad(csv_path)
    if csv_file:
        print(f'  CSV uploaded! URL: {csv_file.get("url", "?")}')
    
    print('\n📤 Uploading JSON file...')
    json_file = upload_file_to_gumroad(json_path)
    if json_file:
        print(f'  JSON uploaded! URL: {json_file.get("url", "?")}')
    
    if csv_file or json_file:
        file_urls = []
        if csv_file: file_urls.append(csv_file.get('url', ''))
        if json_file: file_urls.append(json_file.get('url', ''))
        
        print(f'\n📦 Attaching files to product...')
        # Get existing product
        products = gumroad_get('products').get('products', [])
        bbb_product = [p for p in products if 'BBB' in p.get('name', '')]
        
        if bbb_product:
            pid = bbb_product[0]['id']
            result = update_product(pid, file_urls)
            if result.get('success'):
                print(f'  ✅ Files attached to product!')
                print(f'  URL: https://henryzhangdigital.gumroad.com/l/{bbb_product[0].get("custom_permalink") or ""}')
            else:
                print(f'  ❌ Update failed: {result.get("message", "error")}')
        else:
            print('  Creating new product...')
            result = create_product(
                'BBB Verified Business Leads - Complete Database (747 Leads, 20 Industries)',
                29900,
                '747 verified business leads from Better Business Bureau across 20 industries...',
                file_urls
            )
            if result.get('success'):
                p = result['product']
                print(f'  ✅ Product created!')
                print(f'  URL: {p.get("short_url", "?")}')
    
    print('\n✅ Done!')

if __name__ == '__main__':
    main()
