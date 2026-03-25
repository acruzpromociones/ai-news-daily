import os
import json
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
from anthropic import Anthropic
import schedule
import time
import pytz

# Initialize Anthropic client
client = Anthropic()

# Configuration
GMAIL_USER = os.getenv("GMAIL_USER", "your_email@gmail.com")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD", "your_app_password")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TARGET_EMAIL = "acruz@promocionesfantasticas.com"
TARGET_WHATSAPP = "+573144447492"  # without spaces

BOGOTA_TZ = pytz.timezone('America/Bogota')

def search_ai_news():
    """Search for recent AI news using web search."""
    try:
        response = requests.get(
            "https://news.google.com/rss/search?q=AI+automation+manufacturing+supply+chain&hl=en-US&gl=US&ceid=US:en",
            timeout=10
        )
        
        # Parse RSS feed
        from xml.etree import ElementTree as ET
        root = ET.fromstring(response.content)
        
        articles = []
        for item in root.findall('.//item')[:15]:  # Get top 15 articles
            title = item.findtext('title', '')
            link = item.findtext('link', '')
            pubDate = item.findtext('pubDate', '')
            description = item.findtext('description', '')
            
            if title and link:
                articles.append({
                    'title': title,
                    'link': link,
                    'date': pubDate,
                    'description': description[:200] if description else ''
                })
        
        return articles
    except Exception as e:
        print(f"Error searching news: {e}")
        return []

def filter_and_summarize_news(articles):
    """Use Claude to filter and summarize relevant news."""
    
    if not articles:
        return "No articles found today."
    
    # Prepare articles for Claude
    articles_text = "\n\n".join([
        f"Title: {a['title']}\nLink: {a['link']}\nDescription: {a['description']}"
        for a in articles[:10]
    ])
    
    prompt = f"""Eres un experto en operaciones, manufactura y supply chain.

Tu tarea: Analizar estas noticias de IA y filtrar SOLO las que sean relevantes para:
1. Automatización de procesos operativos
2. IA en manufactura y control de calidad
3. Optimización de supply chain con IA
4. Opciones reales de IA para reducir dependencia de personal

CRITERIO ESTRICTO: Solo incluye noticias que tengan aplicación práctica inmediata en empresa de manufactura/operaciones.

Noticias encontradas:
{articles_text}

RESPONDE EXACTAMENTE EN ESTE FORMATO JSON (sin markdown, solo JSON puro):
{{
  "resumen_ejecutivo": "1-2 líneas del contexto del día",
  "noticias_relevantes": [
    {{
      "titulo": "título",
      "aplicabilidad": "cómo aplica específicamente a manufactura/ops",
      "enlace": "URL",
      "prioridad": "ALTA/MEDIA/BAJA"
    }}
  ],
  "recomendacion_accion": "qué deberías revisar primero hoy"
}}

Si NO hay noticias relevantes, retorna:
{{"resumen_ejecutivo": "Sin noticias relevantes hoy", "noticias_relevantes": [], "recomendacion_accion": ""}}
"""
    
    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Extract JSON from response
        response_text = response.content[0].text
        
        # Try to parse JSON
        try:
            # Remove markdown code blocks if present
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            data = json.loads(response_text.strip())
            return data
        except json.JSONDecodeError:
            print(f"Could not parse JSON: {response_text[:200]}")
            return {"resumen_ejecutivo": "Error procesando noticias", "noticias_relevantes": []}
            
    except Exception as e:
        print(f"Error with Claude: {e}")
        return {"resumen_ejecutivo": "Error procesando noticias", "noticias_relevantes": []}

def format_email_body(news_data):
    """Format the email body."""
    
    bogota_time = datetime.now(BOGOTA_TZ).strftime("%d de %B de %Y - %H:%M")
    
    html = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1a73e8; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
            .header h1 {{ margin: 0; font-size: 24px; }}
            .header p {{ margin: 5px 0 0 0; font-size: 14px; opacity: 0.9; }}
            .resumen {{ background-color: #f0f0f0; padding: 15px; border-left: 4px solid #1a73e8; margin-bottom: 20px; border-radius: 3px; }}
            .noticia {{ margin-bottom: 20px; padding-bottom: 20px; border-bottom: 1px solid #ddd; }}
            .noticia:last-child {{ border-bottom: none; }}
            .noticia h3 {{ margin: 0 0 10px 0; color: #1a73e8; }}
            .noticia p {{ margin: 8px 0; }}
            .aplicabilidad {{ background-color: #e8f5e9; padding: 10px; border-radius: 3px; margin: 10px 0; }}
            .prioridad {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; margin: 5px 0; }}
            .alta {{ background-color: #ffcdd2; color: #c62828; }}
            .media {{ background-color: #ffe0b2; color: #e65100; }}
            .baja {{ background-color: #c8e6c9; color: #2e7d32; }}
            .enlace {{ color: #1a73e8; text-decoration: none; }}
            .recomendacion {{ background-color: #fff9c4; padding: 15px; border-left: 4px solid #fbc02d; border-radius: 3px; margin-top: 20px; }}
            .footer {{ text-align: center; margin-top: 30px; font-size: 12px; color: #999; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📊 AI News Daily</h1>
                <p>Automatización, Manufactura & Supply Chain | {bogota_time}</p>
            </div>
            
            <div class="resumen">
                <strong>Resumen del día:</strong> {news_data.get('resumen_ejecutivo', 'N/A')}
            </div>
    """
    
    noticias = news_data.get('noticias_relevantes', [])
    
    if noticias:
        html += "<h2>Noticias Relevantes:</h2>"
        
        for idx, noticia in enumerate(noticias, 1):
            prioridad = noticia.get('prioridad', 'MEDIA').lower()
            html += f"""
            <div class="noticia">
                <h3>{idx}. {noticia.get('titulo', 'Sin título')}</h3>
                <span class="prioridad {prioridad}">Prioridad: {noticia.get('prioridad', 'N/A')}</span>
                <div class="aplicabilidad">
                    <strong>Aplicabilidad:</strong> {noticia.get('aplicabilidad', 'N/A')}
                </div>
                <p><a href="{noticia.get('enlace', '#')}" class="enlace">Leer más →</a></p>
            </div>
            """
    else:
        html += "<p style='text-align: center; color: #999;'>No hay noticias relevantes hoy.</p>"
    
    if news_data.get('recomendacion_accion'):
        html += f"""
        <div class="recomendacion">
            <strong>🎯 Recomendación:</strong> {news_data.get('recomendacion_accion')}
        </div>
        """
    
    html += """
            <div class="footer">
                <p>Este es un resumen automatizado filtrado para automatización de procesos, manufactura y supply chain.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html

def format_whatsapp_message(news_data):
    """Format message for WhatsApp."""
    
    bogota_time = datetime.now(BOGOTA_TZ).strftime("%d/%m/%Y %H:%M")
    
    message = f"""📊 *AI News Daily*
{bogota_time}

*Resumen:*
{news_data.get('resumen_ejecutivo', 'Sin resumen')}

"""
    
    noticias = news_data.get('noticias_relevantes', [])
    
    if noticias:
        message += "*Noticias relevantes:*\n"
        for idx, noticia in enumerate(noticias[:3], 1):  # Top 3 for WhatsApp
            message += f"""
{idx}. *{noticia.get('titulo', 'Sin título')}*
   Prioridad: {noticia.get('prioridad', 'N/A')}
   {noticia.get('aplicabilidad', 'N/A')}
   {noticia.get('enlace', '')}
"""
    else:
        message += "Sin noticias relevantes hoy.\n"
    
    if news_data.get('recomendacion_accion'):
        message += f"\n🎯 *Acción:* {news_data.get('recomendacion_accion')}"
    
    return message

def send_email(subject, html_body):
    """Send email via Gmail."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = GMAIL_USER
        msg['To'] = TARGET_EMAIL
        
        part = MIMEText(html_body, 'html')
        msg.attach(part)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, TARGET_EMAIL, msg.as_string())
        
        print(f"✓ Email sent to {TARGET_EMAIL}")
        return True
    except Exception as e:
        print(f"✗ Email error: {e}")
        return False

def send_whatsapp(message):
    """Send message via WhatsApp using Twilio."""
    try:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            print("⚠ WhatsApp: Twilio credentials not configured")
            return False
        
        # Twilio API endpoint
        url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"
        
        # Twilio uses a special WhatsApp sender number format
        # For sandbox, it's typically: whatsapp:+14155552671 (Twilio's sandbox number)
        # You need to use the actual WhatsApp Business Account sender number in production
        twilio_whatsapp_sender = "whatsapp:+14155552671"  # Twilio sandbox number
        twilio_whatsapp_receiver = f"whatsapp:{TARGET_WHATSAPP}"
        
        data = {
            "From": twilio_whatsapp_sender,
            "To": twilio_whatsapp_receiver,
            "Body": message
        }
        
        response = requests.post(
            url,
            data=data,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=10
        )
        
        if response.status_code in [200, 201]:
            print(f"✓ WhatsApp sent to {TARGET_WHATSAPP}")
            return True
        else:
            print(f"⚠ WhatsApp error: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"⚠ WhatsApp error: {e}")
        return False

def job():
    """Main job to run every day at 6am Bogotá time."""
    print(f"\n{'='*60}")
    print(f"[{datetime.now(BOGOTA_TZ)}] Starting AI News Daily job...")
    print(f"{'='*60}")
    
    # Search for news
    print("Searching for AI news...")
    articles = search_ai_news()
    print(f"Found {len(articles)} articles")
    
    # Filter and summarize
    print("Filtering and summarizing with Claude...")
    news_data = filter_and_summarize_news(articles)
    
    # Format and send
    subject = f"AI News Daily - {datetime.now(BOGOTA_TZ).strftime('%d/%m/%Y')}"
    
    email_body = format_email_body(news_data)
    send_email(subject, email_body)
    
    whatsapp_msg = format_whatsapp_message(news_data)
    send_whatsapp(whatsapp_msg)
    
    print("Job completed successfully!")

def schedule_job():
    """Schedule the job to run at 6am Bogotá time every day."""
    schedule.every().day.at("06:00").do(job)
    
    print("Scheduler initialized. Running at 6:00 AM Bogotá time daily.")
    
    # Keep scheduler running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # For testing: uncomment to run immediately
    # job()
    
    # For production: run scheduler
    schedule_job()
