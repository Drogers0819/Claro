FinTrack — AI Personal Financial Intelligence Platform
Show Image
<!-- [![Live Demo](https://img.shields.io/badge/demo-live-success)](https://your-app.onrender.com) -->

The only product that combines financial consequence simulation, behavioural pattern recognition, proactive spending intelligence, and a personalised conversational financial companion — built for UK professionals aged 22–35.

Currently in development — v1.0 MVP

The Problem
63% of UK adults describe themselves as "not confident" in their financial understanding. The reason isn't that they lack data — it's that they can't connect today's spending decisions to tomorrow's reality. Existing finance apps tell you what you did spend. FinTrack shows you what your spending habits will cost you over the next 20 years.
The Product
FinTrack is built on three layers:
LayerWhat It DoesFinancial SimulatorModels long-term consequences of current spending across 5, 10, and 20-year horizonsProactive IntelligenceML observes patterns, anticipates high-risk spending moments, and sends nudges before overspending happensFinancial CompanionConversational AI with full access to your financial picture for genuine, personalised dialogue
Current Status
🚧 Week 0 — Planning & Architecture

 Project plan with all technical decisions documented
 Database schema designed
 API endpoints planned
 Folder structure created
 v1.0 — Auth + transaction CRUD
 v2.0 — Analytics, goals, fact-find questionnaire
 v3.0 — Financial simulator + ML intelligence
 v4.0 — Proactive nudges, budgets, anomaly detection
 v5.0 — Stripe subscriptions, chatbot, production deployment

Tech Stack
LayerTechnologyWhyLanguagePython 3.12+Industry standard for backend + MLBackendFlaskLightweight, flexible, great for APIsDatabaseSQLite → PostgreSQLSimple start, production-ready upgradeORMSQLAlchemy + AlembicIndustry standard, migration supportFrontendJinja2 + Chart.jsShip fast, modernise laterMLscikit-learn + pandasRight tool for classification and regressionAuthFlask-Login + Flask-BcryptSession management + password hashingPaymentsStripeIndustry standard, no monthly feeChatbotAnthropic API (Claude)Strong safety guardrails for financial contextTestingpytestClean syntax, excellent fixturesCI/CDGitHub ActionsFree, integrated with repoDeploymentRenderFree tier, Git auto-deploy, PostgreSQL addon
Architecture
Browser
  ↓
Flask Routes          ← HTTP handling, auth, subscription gating
  ↓
Services              ← Business logic (thick layer)
  ↓
Data Pipelines        ← Cleaning, validation, feature engineering
  ↓
Models / ORM          ← Database abstraction
  ↓
SQLite → PostgreSQL

ML Engine             ← Training, prediction, model management
Simulator Engine      ← Projection calculations, scenario modelling
Chatbot Service       ← LLM API, context builder, compliance guardrails
Notification Service  ← Nudge scheduling, email delivery
Subscription Service  ← Stripe integration, trial management
See detailed architecture →
Quick Start
bash# Clone the repository
git clone https://github.com/YOUR_USERNAME/fintrack.git
cd fintrack

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your values

# Run the application
python app.py
Visit http://localhost:5000
Testing
bashpytest tests/
Documentation

Architecture Overview
API Reference
ML Pipeline
Data Pipelines
Deployment Guide
Ethics & Compliance
Development Journal

Regulatory Position
FinTrack operates within the unregulated financial guidance space. It presents data-driven projections and educational information only. It never makes personal recommendations on specific financial products. See Ethics & Compliance for full details.
What I Learned
This section will be completed at v5.0 — documenting the full learning journey from planning to production.
Roadmap
Completed

 v1.0 — Foundation: Auth + transaction CRUD
 v2.0 — Analytics: Goals, categories, fact-find
 v3.0 — Intelligence: Simulator + ML
 v4.0 — Proactive: Nudges, budgets, anomalies
 v5.0 — Launch: Subscriptions, chatbot, deployment

Future

 v6.0 — React frontend rebuild
 v6.1 — Open banking sync (TrueLayer)
 v6.2 — Couples/household finance mode
 v6.3 — Mortgage readiness tool

Licence
MIT