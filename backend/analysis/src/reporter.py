"""
Phase 30: Intelligence Report Pro
PDF Report Generator using WeasyPrint + Jinja2
"""
import json
import base64
from datetime import datetime
from jinja2 import Template

# WeasyPrint import - will fail if not installed
try:
    from weasyprint import HTML, CSS
except ImportError:
    HTML = None
    CSS = None

REPORT_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }
        body {
            font-family: 'Helvetica Neue', Arial, sans-serif;
            color: #1e293b;
            line-height: 1.6;
        }
        .cover {
            text-align: center;
            padding: 100px 0;
            page-break-after: always;
        }
        .cover h1 {
            font-size: 36px;
            color: #2563eb;
            margin-bottom: 10px;
        }
        .cover .subtitle {
            font-size: 18px;
            color: #64748b;
        }
        .cover .target {
            font-size: 24px;
            margin: 40px 0;
            padding: 20px;
            background: #f1f5f9;
            border-radius: 8px;
            word-break: break-all;
        }
        .cover .date {
            color: #94a3b8;
            font-size: 14px;
        }
        h2 {
            color: #2563eb;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 8px;
            margin-top: 30px;
        }
        .summary-box {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .summary-grid {
            display: flex;
            gap: 20px;
        }
        .summary-item {
            flex: 1;
            text-align: center;
            padding: 15px;
            background: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        .summary-item .value {
            font-size: 32px;
            font-weight: bold;
            color: #2563eb;
        }
        .summary-item .label {
            font-size: 12px;
            color: #64748b;
            text-transform: uppercase;
        }
        .entity-card {
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            background: white;
        }
        .entity-card.high-priority {
            border-left: 4px solid #ef4444;
        }
        .entity-card.key-entity {
            border-left: 4px solid #eab308;
        }
        .entity-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .entity-name {
            font-size: 18px;
            font-weight: bold;
        }
        .entity-type {
            background: #e2e8f0;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            text-transform: uppercase;
        }
        .priority-badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-weight: bold;
            font-size: 14px;
        }
        .priority-high { background: #fecaca; color: #991b1b; }
        .priority-medium { background: #fed7aa; color: #9a3412; }
        .priority-low { background: #e2e8f0; color: #475569; }
        .anomaly-badge {
            background: #fecaca;
            color: #991b1b;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .graph-container {
            text-align: center;
            margin: 20px 0;
            page-break-before: always;
        }
        .graph-container img {
            max-width: 100%;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
        }
        .footer {
            text-align: center;
            font-size: 10px;
            color: #94a3b8;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e2e8f0;
        }
    </style>
</head>
<body>
    <!-- Cover Page -->
    <div class="cover">
        <h1>🔍 INVESTIDUBH</h1>
        <p class="subtitle">Intelligence Report</p>
        <div class="target">{{ investigation.target_url }}</div>
        <p class="date">Generated: {{ generated_date }}</p>
    </div>

    <!-- Executive Summary -->
    <h2>📊 Executive Summary</h2>
    <div class="summary-box">
        <div class="summary-grid">
            <div class="summary-item">
                <div class="value">{{ stats.total_nodes }}</div>
                <div class="label">Entities</div>
            </div>
            <div class="summary-item">
                <div class="value">{{ stats.total_edges }}</div>
                <div class="label">Relationships</div>
            </div>
            <div class="summary-item">
                <div class="value">{{ stats.avg_priority }}</div>
                <div class="label">Avg Priority</div>
            </div>
        </div>
    </div>

    <!-- Key Findings -->
    <h2>🔑 Key Findings</h2>
    {% if top_entities %}
    {% for entity in top_entities %}
    <div class="entity-card key-entity">
        <div class="entity-header">
            <span class="entity-name">{{ entity.label }}</span>
            <span class="entity-type">{{ entity.type }}</span>
        </div>
        <div>
            <span class="priority-badge priority-high">Priority: {{ entity.priority }}</span>
            <span style="margin-left: 10px; color: #64748b;">Degree: {{ entity.degree }}</span>
        </div>
    </div>
    {% endfor %}
    {% else %}
    <p>No key entities identified.</p>
    {% endif %}

    <!-- Anomalies & Risks -->
    <h2>⚠️ Anomalies & Risks</h2>
    {% if anomalies %}
    {% for anomaly in anomalies %}
    <div class="entity-card high-priority">
        <div class="entity-header">
            <span class="entity-name">{{ anomaly.label }}</span>
            <span class="anomaly-badge">{{ anomaly.spike_ratio }}x spike</span>
        </div>
        <p style="color: #64748b; margin: 5px 0;">{{ anomaly.reason }}</p>
    </div>
    {% endfor %}
    {% else %}
    <p>No anomalies detected.</p>
    {% endif %}

    <!-- Relationship Map -->
    {% if graph_image %}
    <div class="graph-container">
        <h2>🕸️ Relationship Map</h2>
        <img src="{{ graph_image }}" alt="Investigation Graph">
    </div>
    {% endif %}

    <div class="footer">
        Generated by Investidubh — Commercial-Grade OSINT Platform<br>
        {{ generated_date }}
    </div>
</body>
</html>
"""


def generate_report(
    investigation: dict,
    insights: dict,
    graph_image_base64: str = None
) -> bytes:
    """
    Generate PDF report from investigation data.
    
    Args:
        investigation: { id, target_url, status, created_at }
        insights: { top_entities, anomalies, stats }
        graph_image_base64: Base64-encoded PNG image of the graph
    
    Returns:
        PDF binary data
    """
    if HTML is None:
        raise ImportError("WeasyPrint is not installed. Run: pip install weasyprint")
    
    template = Template(REPORT_TEMPLATE)
    
    html_content = template.render(
        investigation=investigation,
        top_entities=insights.get('top_entities', []),
        anomalies=insights.get('anomalies', []),
        stats=insights.get('stats', {}),
        graph_image=graph_image_base64,
        generated_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    
    pdf_bytes = HTML(string=html_content).write_pdf()
    return pdf_bytes


if __name__ == "__main__":
    # Test generation
    test_investigation = {
        "id": "test-123",
        "target_url": "https://example.com",
        "status": "COMPLETED"
    }
    test_insights = {
        "top_entities": [
            {"label": "John Smith", "type": "person", "priority": 85, "degree": 5},
            {"label": "ACME Corp", "type": "organization", "priority": 78, "degree": 4}
        ],
        "anomalies": [
            {"label": "suspicious.com", "spike_ratio": 4.5, "reason": "Frequency spike: 4.5x normal"}
        ],
        "stats": {
            "total_nodes": 45,
            "total_edges": 78,
            "avg_priority": 42
        }
    }
    
    try:
        pdf = generate_report(test_investigation, test_insights)
        with open("test_report.pdf", "wb") as f:
            f.write(pdf)
        print("[✓] Test report generated: test_report.pdf")
    except ImportError as e:
        print(f"[!] {e}")
