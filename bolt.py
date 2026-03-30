#!/usr/bin/env python3
"""
OTP Monitor Bot - Railway Deployment (Full Debug)
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

app = Flask(__name__)

# ========== CONFIGURATION ==========
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8618305528:AAF64PwFIlsw091Hbns8fGQqvwVSW6_4iCY")
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "-1001153782407")
SESSION_COOKIE = os.environ.get("SESSION_COOKIE", "c685ad79ac6910d642978e8bd0ba450e")
TARGET_URL = os.environ.get("TARGET_URL", "http://144.217.71.192/ints/agent/res/data_smscdr.php")
# ====================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG
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
        logger.info("✅ OTP Monitor Bot initialized")
    
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
        if not isinstance(message, str):
            message = str(message)
        match = self.otp_regex.search(message)
        return match.group(0) if match else None
    
    def create_otp_id(self, timestamp, phone, message):
        otp = self.extract_otp(message) or str(message)[:20]
        return f"{timestamp}_{phone}_{otp}"
    
    def safe_str(self, value):
        if value is None:
            return ""
        return str(value)
    
    def format_message(self, sms_data):
        """Format SMS data for Telegram"""
        try:
            # Try to extract data from the list
            if isinstance(sms_data, list):
                # Log what we have
                logger.info(f"📝 Formatting SMS with {len(sms_data)} fields")
                
                # Based on the original SMS list format you provided earlier
                # Format: [timestamp, operator, number, platform, ?, message, ...]
                timestamp = self.safe_str(sms_data[0]) if len(sms_data) > 0 else ""
                operator = self.safe_str(sms_data[1]) if len(sms_data) > 1 else ""
                phone = self.safe_str(sms_data[2]) if len(sms_data) > 2 else ""
                platform = self.safe_str(sms_data[3]) if len(sms_data) > 3 else ""
                message = self.safe_str(sms_data[5]) if len(sms_data) > 5 else ""
                
                # Check if we got valid data
                if timestamp and phone and phone != "0":
                    # Hide phone number
                    if len(phone) >= 8:
                        hidden_phone = phone[:4] + "****" + phone[-4:]
                    else:
                        hidden_phone = phone
                    
                    operator_name = operator.split()[0] if operator else ""
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
                else:
                    # If data seems invalid, show raw data for debugging
                    return f"""
⚠️ **SMS Data Received** ⚠️

**Raw Data:**
`{sms_data[:6]}`

**Timestamp:** {timestamp}
**Phone:** {phone}
**Operator:** {operator}
**Platform:** {platform}

🤖 @updaterange
"""
            return "No valid SMS data"
        except Exception as e:
            logger.error(f"Format error: {e}")
            return f"Error: {e}\nData: {sms_data[:3]}"
    
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) Chrome/145.0.0.0 Mobile Safari/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Cookie": f"PHPSESSID={SESSION_COOKIE}",
            "Referer": "http://144.217.71.192/ints/agent/SMSCDRReports",
        }
        
        current_date = time.strftime("%Y-%m-%d")
        params = {
            "fdate1": f"{current_date} 00:00:00",
            "fdate2": f"{current_date} 23:59:59",
            "fg": "0",
            "sEcho": "1",
            "iColumns": "9",
            "iDisplayStart": "0",
            "iDisplayLength": "50",
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
                                data = json.loads(text)
                                # Log the FULL structure of first record
                                if data.get("aaData") and len(data["aaData"]) > 0:
                                    first_record = data["aaData"][0]
                                    logger.info("=" * 60)
                                    logger.info("📊 FULL DATA STRUCTURE:")
                                    logger.info(f"Type: {type(first_record)}")
                                    logger.info(f"Length: {len(first_record) if hasattr(first_record, '__len__') else 'N/A'}")
                                    logger.info(f"Content: {first_record}")
                                    logger.info("=" * 60)
                                return data
                        else:
                            logger.warning(f"HTTP {resp.status}")
            else:
                def sync_fetch():
                    resp = requests.get(TARGET_URL, headers=headers, params=params, timeout=15, verify=False)
                    if resp.status_code == 200 and resp.text and resp.text.strip():
                        data = resp.json()
                        if data.get("aaData") and len(data["aaData"]) > 0:
                            first_record = data["aaData"][0]
                            logger.info("=" * 60)
                            logger.info("📊 FULL DATA STRUCTURE:")
                            logger.info(f"Type: {type(first_record)}")
                            logger.info(f"Length: {len(first_record) if hasattr(first_record, '__len__') else 'N/A'}")
                            logger.info(f"Content: {first_record}")
                            logger.info("=" * 60)
                        return data
                    return None
                return await asyncio.to_thread(sync_fetch)
        except Exception as e:
            logger.warning(f"Fetch error: {e}")
            return None
    
    async def monitor_loop(self):
        logger.info("🚀 Starting OTP monitoring...")
        
        # Send startup
        await self.send_telegram_message(f"🚀 **Bot Started**\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n📡 Monitoring for OTPs...")
        
        consecutive_failures = 0
        
        while self.is_monitoring:
            try:
                data = await self.fetch_sms_data()
                
                if data and data.get("aaData"):
                    consecutive_failures = 0
                    sms_list = data["aaData"]
                    logger.info(f"📥 Received {len(sms_list)} SMS records")
                    
                    # Process each SMS
                    for idx, sms in enumerate(sms_list):
                        try:
                            logger.info(f"🔍 Processing SMS #{idx}: {sms[:5] if len(sms) > 5 else sms}")
                            
                            # Create a unique ID
                            sms_str = json.dumps(sms)
                            if sms_str not in self.processed_otps:
                                logger.info(f"🚨 New SMS found! Sending to Telegram...")
                                
                                formatted = self.format_message(sms)
                                if await self.send_telegram_message(formatted):
                                    self.processed_otps.add(sms_str)
                                    self.total_otps_sent += 1
                                    self._save_processed_otps()
                                    logger.info(f"✅ SMS #{self.total_otps_sent} sent")
                                    
                                    # Wait 2 seconds before next
                                    await asyncio.sleep(2)
                            else:
                                logger.debug(f"⏭️ SMS already processed")
                                
                        except Exception as e:
                            logger.error(f"Error processing SMS {idx}: {e}")
                            continue
                    
                    await asyncio.sleep(2)
                else:
                    consecutive_failures += 1
                    wait_time = min(consecutive_failures * 2, 10)
                    logger.debug(f"No data (attempt {consecutive_failures})")
                    await asyncio.sleep(wait_time)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Loop error: {e}")
                await asyncio.sleep(5)

@app.route('/')
@app.route('/health')
def health():
    return jsonify({"status": "running", "time": datetime.now().isoformat()})

def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot = OTPMonitorBot()
    try:
        loop.run_until_complete(bot.monitor_loop())
    except Exception as e:
        logger.error(f"Bot error: {e}")

if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)