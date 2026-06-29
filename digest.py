#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import requests
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ===== КОНФИГУРАЦИЯ =====
NEWS_API_KEY = os.environ.get('NEWS_API_KEY')
GMAIL_USER = os.environ.get('GMAIL_USER')
GMAIL_APP_PASSWORD = os.environ.get('GMAIL_APP_PASSWORD')
TO_EMAIL = os.environ.get('TO_EMAIL')

SPREADSHEET_NAME = "News_Digest"
SERVICE_ACCOUNT_FILE = 'credentials.json'
TOPIC = "world"
DAYS_BACK = 1
MAX_ARTICLES = 15

# ===== ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS =====
def init_google_sheet():
    scope = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=scope)
    client = gspread.authorize(creds)
    
    try:
        sheet = client.open(SPREADSHEET_NAME).sheet1
        print(f"✅ Таблица '{SPREADSHEET_NAME}' открыта")
    except:
        sheet = client.create(SPREADSHEET_NAME).sheet1
        print(f"✅ Таблица '{SPREADSHEET_NAME}' создана")
        sheet.append_row(["Дата сбора", "Ранг", "Заголовок", "Источник", "Дата публикации", "Ссылка", "Описание"])
    
    return sheet

# ===== ЗАПРОС К NEWSAPI =====
def fetch_top_news():
    from_date = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': TOPIC,
        'from': from_date,
        'sortBy': 'popularity',
        'language': 'ru',
        'pageSize': MAX_ARTICLES,
        'apiKey': NEWS_API_KEY
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = data.get('articles', [])
            print(f"✅ Получено {len(articles)} новостей")
            return articles
        else:
            print(f"❌ Ошибка API: {data.get('message', 'Unknown error')}")
            return []
    except Exception as e:
        print(f"❌ Ошибка запроса: {e}")
        return []

# ===== ЗАПИСЬ В GOOGLE SHEETS =====
def save_to_sheet(sheet, articles):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    rows = []
    for rank, article in enumerate(articles, 1):
        title = article.get('title', 'Нет заголовка')
        source = article.get('source', {}).get('name', 'Неизвестный источник')
        published = article.get('publishedAt', '')
        url = article.get('url', '')
        description = article.get('description', '')[:200] if article.get('description') else ''
        rows.append([now_str, f"#{rank}", title, source, published, url, description])
    
    if rows:
        sheet.append_rows(rows)
        print(f"✅ Записано {len(rows)} строк в Google Sheets")

# ===== ОТПРАВКА EMAIL =====
def send_email(articles):
    if not articles:
        print("Нет новостей для отправки")
        return
    
    html_body = f"""
    <html>
    <head><meta charset="utf-8"></head>
    <body>
    <h2>📰 Топ-{len(articles)} новостей за {datetime.now().strftime('%d.%m.%Y')}</h2>
    <p>Тема: <strong>{TOPIC}</strong></p>
    <ol>
    """
    for article in articles:
        title = article.get('title', 'Нет заголовка')
        url = article.get('url', '#')
        source = article.get('source', {}).get('name', 'Неизвестный источник')
        html_body += f'<li><b><a href="{url}">{title}</a></b> — {source}</li>'
    
    html_body += """
    </ol>
    <hr>
    <small>Хорошего дня!❤️</small>
    </body>
    </html>
    """
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = f"📰 Топ новостей за {datetime.now().strftime('%d.%m.%Y')}"
    msg['From'] = GMAIL_USER
    msg['To'] = TO_EMAIL
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        server.send_message(msg)
        server.quit()
        print(f"✅ Письмо отправлено на {TO_EMAIL}")
    except Exception as e:
        print(f"❌ Ошибка отправки письма: {e}")

def main():
    print("🚀 Запуск ежедневного дайджеста новостей")
    sheet = init_google_sheet()
    articles = fetch_top_news()
    if not articles:
        print("Новости не найдены, завершаем")
        return
    save_to_sheet(sheet, articles)
    send_email(articles)
    print("✅ Дайджест успешно сформирован и отправлен")

if __name__ == "__main__":
    main()
