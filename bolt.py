# ========== কনফিগারেশন – আপনার তথ্য দিয়ে পূরণ করা আছে ==========
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "8618305528:AAF64PwFIlsw091Hbns8fGQqvwVSW6_4iCY"
)
GROUP_CHAT_ID = os.getenv(
    "GROUP_CHAT_ID",
    "-1001153782407"
)
# ✅ সঠিক URL (আপনার HTTP request এর Host থেকে)
SESSION_COOKIE = os.getenv(
    "SESSION_COOKIE",
    "c685ad79ac6910d642978e8bd0ba450e"
)
# ✅ সঠিক URL আপডেট করুন
TARGET_URL = os.getenv(
    "TARGET_URL",
    "http://144.217.71.192/ints/agent/res/data_smscdr.php"  # ✅ এইটা ঠিক করুন
)