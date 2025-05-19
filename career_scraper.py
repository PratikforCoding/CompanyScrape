import os
import time
import json
from googlesearch import search
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import gspread
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# ===== CONFIGURATION FROM ENV =====
DOC_ID = os.getenv('GOOGLE_DOC_ID')
SHEET_TITLE = os.getenv('GOOGLE_SHEET_TITLE')
CSE_API_KEY = os.getenv('GOOGLE_CSE_API_KEY')
CSE_ID = os.getenv('GOOGLE_CSE_ID')
SERVICE_ACCOUNT_JSON = 'secrets/credentials.json'

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/documents.readonly'
]

creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_JSON, scopes=SCOPES)

# ===== UTILITY FUNCTIONS =====
def get_text(cell):
    text = ''
    for content in cell.get('content', []):
        for element in content.get('paragraph', {}).get('elements', []):
            text += element.get('textRun', {}).get('content', '')
    return text.strip()

def get_company_list_from_doc(doc_id):
    print("📄 Fetching company names from Google Docs...")
    doc_service = build('docs', 'v1', credentials=creds)
    document = doc_service.documents().get(documentId=doc_id).execute()
    companies = []

    try:
        for element in document.get('body', {}).get('content', []):
            if 'table' in element:
                table = element['table']
                for row in table.get('tableRows', [])[1:]:  # Skip header
                    cells = row.get('tableCells', [])
                    if len(cells) >= 2:
                        company = get_text(cells[1])
                        if company:
                            companies.append(company)
    except Exception as e:
        print("❌ Error reading document:", e)

    print(f"✅ Found {len(companies)} companies")
    return companies

def find_career_site(company):
    query = f"{company} careers site India"
    try:
        for url in search(query, num_results=5):
            if any(keyword in url.lower() for keyword in ['careers', 'jobs', 'joinus', 'join-us', 'work-with-us']):
                return url
    except Exception as e:
        print(f"❌ Google search failed for {company}: {e}")
    return ''

def append_career_sites_to_sheet(sheet_title, data):
    print("📊 Connecting to Google Sheet...")
    gc = gspread.authorize(creds)
    sheet = gc.open(sheet_title).sheet1

    existing = sheet.get_all_records()
    existing_companies = set(row['Company'].strip().lower() for row in existing if row.get('Company'))

    for company, url in data:
        if company.strip().lower() in existing_companies:
            print(f"⏭️ Skipping {company} (already in sheet)")
            continue
        print(f"✅ Adding {company}: {url}")
        sheet.append_row([company, url, '', '', '', ''])
        time.sleep(1)  # Delay to avoid rate limits

# ===== MAIN =====
if __name__ == '__main__':
    companies = get_company_list_from_doc(DOC_ID)
    results = []

    for company in companies:
        print(f"🔍 Searching for: {company}")
        url = find_career_site(company)
        results.append((company, url))
        time.sleep(1)  # Delay between search queries

    append_career_sites_to_sheet(SHEET_TITLE, results)
