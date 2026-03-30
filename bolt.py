#!/usr/bin/env python3
"""
OTP Monitor Bot - Railway Deployment (Fixed)
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from flask import Flask, jsonify
import threading

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False
    import requests
    import urllib3
    urllib3.disable_warnings()

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# Flask app for health check
app = Flask(__name__)

# ========== CONFIGURATION ==========
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8618305528:AAF64PwFIlsw091Hbns8fGQqvwVSW6_4iCY")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "-1001153782407")
SESSION_COOKIE = os.environ.get("SESSION_COOKIE", "c685ad79ac6910d642978e8bd0ba450e")
TARGET_URL = os.environ.get("TARGET_URL", "http://144.217.71.192/ints/agent/res/data_smscdr.php")
# ====================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OTPMonitorBot:
    def __init__(self):
        self.storage_file = "processed_otps.json"
        self.processed_otps = self._load_processed_otps()
        self.total_otps_sent = 0
        self.is_monitoring = True
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        # OTP patterns
        patterns = [
            r'\b\d{4}\b', r'\b\d{5}\b', r'\b\d{6}\b', r'\b\d{3}-\d{3}\b',
            r'code[:\s]*\d+', r'কোড[:\s]*\d+', r'OTP[:\s]*\d+',
            r'verification code[:\s]*\d+', r'Your.*code.*\d+', r'pin[:\s]*\d+',
        ]
        self.otp_regex = re.compile('|'.join(patterns), re.IGNORECASE)
        logger.info("✅ OTP Monitor Bot initialized on Railway")
    
    def _load_processed_otps(self):
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    data = json.load(f)
                cutoff = datetime.now() - timedelta(hours=24)
                return {k for k, v in data.items() if datetime.fromisoformat(v) > cutoff}
        except Exception as e:
            logger.error(f"Error loading: {e}")
        return set()
    
    def _save_processed_otps(self):
        try:
            data = {otp_id: datetime.now().isoformat() for otp_id in self.processed_otps}
            with open(self.storage_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.error(f"Error saving: {e}")
    
    def extract_otp(self, message):
        """Extract OTP from message string"""
        if not isinstance(message, str):
            message = str(message)
        match = self.otp_regex.search(message)
        return match.group(0) if match else None
    
    def create_otp_id(self, timestamp, phone, message):
        """Create unique OTP ID"""
        otp = self.extract_otp(message) or str(message)[:20]
        return f"{timestamp}_{phone}_{otp}"
    
    def safe_str(self, value):
        """Convert any value to string safely"""
        if value is None:
            return ""
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)
    
    def format_message(self, sms):
        """Format SMS data to Telegram message"""
        try:
            # Safely extract data with type checking
            timestamp = self.safe_str(sms[0]) if len(sms) > 0 else ""
            operator = self.safe_str(sms[1]) if len(sms) > 1 else ""
            phone = self.safe_str(sms[2]) if len(sms) > 2 else ""
            platform = self.safe_str(sms[3]) if len(sms) > 3 else ""
            message = self.safe_str(sms[5]) if len(sms) > 5 else ""
            
            # Hide phone number
            if len(phone) >= 8:
                hidden_phone = phone[:4] + "****" + phone[-4:]
            else:
                hidden_phone = phone or "Unknown"
            
            # Extract operator name
            operator_name = operator.split()[0] if operator else ""
            
            # Extract OTP
            otp = self.extract_otp(message) or "Processing..."
            
            return f"""
🔥 **OTP Detected!** 🔥
━━━━━━━━━━━━━━━━━━━━

📅 **Time:** `{timestamp}`
📱 **Number:** `{hidden_phone}`
🏢 **Operator:** `{operator_name}`
📟 **Platform:** `{platform}`

🔐 **OTP Code:** `{otp}`

📝 **Message:**
`{message[:200]}`

━━━━━━━━━━━━━━━━━━━━
🤖 @updaterange
"""
        except Exception as e:
            logger.error(f"Error formatting message: {e}")
            return f"🔥 OTP Detected!\nCheck logs for details"
    
    async def send_telegram_message(self, message):
        try:
            keyboard = [
                [InlineKeyboardButton("📢 Main Channel", url="https://t.me/updaterange")],
                [InlineKeyboardButton("🤖 Number Bot", url="https://t.me/Updateotpnew_bot")],
                [InlineKeyboardButton("👨‍💻 Developer", url="https://t.me/rana1132")],
            ]
            await self.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=message,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
            return True
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False
    
    async def fetch_sms_data(self):
        """Fetch SMS data from API"""
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) Chrome/145.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"PHPSESSID={SESSION_COOKIE}",
            "Referer": "http://144.217.71.192/ints/agent/SMSCDRReports",
            "Connection": "keep-alive",
        }
        
        current_date = time.strftime("%Y-%m-%d")
        params = {
            "fdate1": f"{current_date} 00:00:00",
            "fdate2": f"{current_date} 23:59:59",
            "frange": "",
            "fclient": "",
            "fnum": "",
            "fcli": "",
            "fg": "0",
            "sEcho": "1",
            "iColumns": "9",
            "iDisplayStart": "0",
            "iDisplayLength": "100",  # Increased to get more data
            "sSearch": "",
            "iSortCol_0": "0",
            "sSortDir_0": "desc",
            "iSortingCols": "1",
            "_": str(int(time.time() * 1000)),
        }
        
        try:
            if HAS_AIOHTTP:
                async with aiohttp.ClientSession() as session:
                    async with session.get(TARGET_URL, headers=headers, params=params, timeout=15, ssl=False) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            if text and text.strip():
                                return json.loads(text)
                        else:
                            logger.warning(f"HTTP {resp.status}")
            else:
                def sync_fetch():
                    try:
                        resp = requests.get(TARGET_URL, headers=headers, params=params, timeout=15, verify=False)
                        if resp.status_code == 200 and resp.text and resp.text.strip():
                            return resp.json()
                    except Exception as e:
                        logger.warning(f"Sync fetch error: {e}")
                    return None
                return await asyncio.to_thread(sync_fetch)
        except Exception as e:
            logger.warning(f"Fetch error: {e}")
            return None
        return None
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("🚀 Starting OTP monitoring on Railway...")
        
        # Send startup message
        await self.send_telegram_message(f"🚀 **Bot Started Successfully!**\n\n⏰ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n🌐 Platform: Railway")
        
        consecutive_failures = 0
        
        while self.is_monitoring:
            try:
                data = await self.fetch_sms_data()
                
                if data and data.get("aaData"):
                    consecutive_failures = 0
                    sms_list = data["aaData"]
                    logger.info(f"📥 Received {len(sms_list)} SMS records")
                    
                    # Process oldest first
                    for sms in sms_list:
                        try:
                            # Validate SMS data
                            if not sms or len(sms) < 6:
                                continue
                            
                            # Safely extract data
                            timestamp = self.safe_str(sms[0])
                            phone = self.safe_str(sms[2])
                            message = self.safe_str(sms[5])
                            
                            if not timestamp or not phone:
                                continue
                            
                            otp_id = self.create_otp_id(timestamp, phone, message)
                            
                            if otp_id not in self.processed_otps:
                                logger.info(f"🚨 New OTP: {timestamp} - {phone}")
                                formatted = self.format_message(sms)
                                
                                if await self.send_telegram_message(formatted):
                                    self.processed_otps.add(otp_id)
                                    self.total_otps_sent += 1
                                    self._save_processed_otps()
                                    logger.info(f"✅ OTP #{self.total_otps_sent} sent")
                                    break  # Send only one OTP per cycle
                        except Exception as e:
                            logger.error(f"Error processing SMS: {e}, Data: {sms}")
                            continue
                    
                    await asyncio.sleep(1.0)  # Wait 1 second between checks
                else:
                    consecutive_failures += 1
                    wait_time = min(consecutive_failures * 1.0, 10)
                    logger.warning(f"⚠️ No data or API error (attempt {consecutive_failures}), waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    
            except asyncio.CancelledError:
                logger.info("Monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(3)

# Flask routes
@app.route('/')
def health_check():
    return jsonify({
        "status": "running",
        "time": datetime.now().isoformat(),
        "otps_sent": getattr(app, 'total_otps', 0)
    })

@app.route('/health')
def health():
    return jsonify({"status": "ok"})

def run_bot():
    """Run bot in separate thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = OTPMonitorBot()
    app.total_otps = bot.total_otps_sent
    try:
        loop.run_until_complete(bot.monitor_loop())
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    # Start bot in background thread
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    # Run Flask for health checks
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)