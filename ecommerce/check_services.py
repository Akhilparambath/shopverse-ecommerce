import django, os, sys
sys.path.insert(0, '.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecommerce_project.settings')
django.setup()

from django.conf import settings

# ─────────────────────────────────────
# SMTP CHECK
# ─────────────────────────────────────
print("=" * 40)
print("   SMTP EMAIL SETTINGS")
print("=" * 40)
print(f"HOST:      {settings.EMAIL_HOST}")
print(f"PORT:      {settings.EMAIL_PORT}")
print(f"USE_TLS:   {settings.EMAIL_USE_TLS}")
print(f"USER:      {settings.EMAIL_HOST_USER}")

pwd = settings.EMAIL_HOST_PASSWORD
if pwd and pwd != 'your_email_password':
    print(f"PASSWORD:  [SET — {len(pwd)} chars]")
    real_smtp = True
else:
    print("PASSWORD:  [NOT SET — placeholder only]")
    real_smtp = False

if real_smtp:
    try:
        from django.core.mail import get_connection
        conn = get_connection()
        conn.open()
        conn.close()
        print("STATUS:    ✅ SMTP CONNECTION SUCCESSFUL")
    except Exception as e:
        print(f"STATUS:    ❌ SMTP FAILED — {e}")
else:
    print("STATUS:    ⚠️  Not configured (still using placeholders)")

# ─────────────────────────────────────
# STRIPE CHECK
# ─────────────────────────────────────
print()
print("=" * 40)
print("   STRIPE PAYMENT SETTINGS")
print("=" * 40)
sk = settings.STRIPE_SECRET_KEY
pk = settings.STRIPE_PUBLIC_KEY
print(f"PUBLIC KEY:  {pk[:28]}...")
print(f"SECRET KEY:  {sk[:28]}...")

try:
    import stripe
    stripe.api_key = sk
    bal = stripe.Balance.retrieve()
    avail = bal["available"]
    print(f"STATUS:    ✅ STRIPE CONNECTED")
    for b in avail:
        print(f"           Available ({b['currency'].upper()}): {b['amount'] / 100:.2f}")
except stripe.error.AuthenticationError as e:
    print(f"STATUS:    ❌ AUTH FAILED — invalid API key")
    print(f"           {e}")
except Exception as e:
    print(f"STATUS:    ❌ ERROR — {e}")
