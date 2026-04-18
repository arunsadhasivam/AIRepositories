
# ── HTML template ──
HEALTH_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>RAG Health Monitor</title>
    <meta http-equiv="refresh" content="10">  <!-- auto refresh every 10 seconds -->
    <style>
        body        { font-family: Arial, sans-serif; background: #1e1e1e; color: #fff; padding: 40px; }
        h1          { color: #fff; margin-bottom: 30px; }
        .grid       { display: grid; grid-template-columns: repeat(1, 1fr); gap: 20px; max-width: 600px; }
        .card       { padding: 24px; border-radius: 10px; text-align: center; font-size: 18px; font-weight: bold; }
        .pass       { background: #1a7a3a; border: 2px solid #2ecc71; color: #2ecc71; }
        .fail       { background: #7a1a1a; border: 2px solid #e74c3c; color: #e74c3c; }
        .service    { font-size: 14px; color: #ccc; margin-bottom: 8px; }
        .timestamp  { margin-top: 30px; color: #888; font-size: 13px; }
    </style>
</head>
<body>
    <h1>RAG Service Health Monitor</h1>
    <div class="grid">
        {% for service, status in statuses.items() %}
        <div class="card {{ 'pass' if status else 'fail' }}">
            <div class="service">{{ service }}</div>
            {{ 'PASS' if status else 'FAIL' }}
        </div><br>
        {% endfor %}
    </div>
    <div class="timestamp">Last checked: {{ now }}</div>
</body>
</html>
"""
def getAvailabilityTemplate():
   return HEALTH_TEMPLATE