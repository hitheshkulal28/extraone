"""
Vantix — Custom Presidio Pattern Recognizers
=============================================
This script adds India-specific and developer-specific patterns
that the default Presidio model does not cover.

Usage:
    python presidio_custom.py          → runs a local Flask server on :5002
    docker-based Presidio covers most, this adds the gaps.
"""

from presidio_analyzer import AnalyzerEngine, Pattern, PatternRecognizer
from flask import Flask, request, jsonify

app = Flask(__name__)
analyzer = AnalyzerEngine()

# ── JWT Token ─────────────────────────────────────────────────────────────────
analyzer.registry.add_recognizer(PatternRecognizer(
    supported_entity="JWT_TOKEN",
    patterns=[Pattern("JWT", r"eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", 0.9)]
))

# ── Database connection strings ───────────────────────────────────────────────
analyzer.registry.add_recognizer(PatternRecognizer(
    supported_entity="DB_CONNECTION_STRING",
    patterns=[Pattern("DB", r"(mongodb|mysql|postgresql|redis):\/\/[^\s\"']+", 0.9)]
))

# ── Private IP ────────────────────────────────────────────────────────────────
analyzer.registry.add_recognizer(PatternRecognizer(
    supported_entity="PRIVATE_IP",
    patterns=[Pattern("IP", r"\b(192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\.)\d+\.\d+\b", 0.85)]
))

# ── IFSC Code ─────────────────────────────────────────────────────────────────
analyzer.registry.add_recognizer(PatternRecognizer(
    supported_entity="IFSC_CODE",
    patterns=[Pattern("IFSC", r"[A-Z]{4}0[A-Z0-9]{6}", 0.85)]
))

# ── Bank account number ──────────────────────────────────────────────────────
analyzer.registry.add_recognizer(PatternRecognizer(
    supported_entity="BANK_ACCOUNT",
    patterns=[Pattern("BANK_ACCT", r"\b\d{9,18}\b", 0.6)]
))

# ── API endpoint ──────────────────────────────────────────────────────────────

@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    text = data.get("text", "")
    language = data.get("language", "en")

    results = analyzer.analyze(text=text, language=language, entities=None)

    return jsonify([
        {
            "entity_type": r.entity_type,
            "start": r.start,
            "end": r.end,
            "score": r.score
        }
        for r in results
    ])

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    print("-----------------------------------------")
    print("  Vantix Presidio (Custom) running on :5002")
    print("-----------------------------------------")
    app.run(host="0.0.0.0", port=5002, debug=False)
