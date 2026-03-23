FinTrack — Project Plan
1. Problem Statement

Approximately 63% of UK adults report low confidence in managing their finances. Many of these individuals are intelligent and responsible, yet they make daily financial decisions without understanding their long-term consequences (over 2, 5, or 10 years).

Current solutions fall into two categories:

1. Banking apps and budgeting tools

Track historical spending
Retrospective and passive
Provide data without meaningful insight

2. Financial advisors

Provide forward-looking financial planning
Typically only accessible to high-net-worth individuals due to fees and minimum asset requirements
Market Gap

Young professionals aged 22–35 earning approximately £25,000–£60,000 per year are underserved.

Typical characteristics:

Renting accommodation
Paying into pension schemes they do not fully understand
Attempting to save for a home
Regularly spending on convenience services without recognising long-term impact

Example:

Spending £340/month on food delivery may feel harmless in the present but represents tens of thousands of pounds over a decade when accounting for opportunity cost and investment growth.

FinTrack aims to make these hidden costs visible.

2. Core Insight

People rarely change financial behaviour because they lack information.

They change behaviour when they viscerally understand the consequences of their choices.

FinTrack’s mission is to:

Make financial trade-offs visible
Present spending consequences clearly
Deliver insights that are personal and emotionally meaningful

Existing tools tend to be:

Tedious (manual spreadsheets)
Bloated with unused features
Locked behind premium paywalls

FinTrack focuses on delivering simple, intelligent insights without unnecessary complexity.

3. MVP (v1.0)
Objective

Launch a functional prototype quickly to validate the core concept.

Features
Manual transaction entry via web form
View transactions in a list
Delete transactions
Persistent storage using SQLite
Display total spending
Design Principle

Even at MVP stage, features should support the core insight:

Helping users understand how daily spending affects their long-term finances.

MVP Success Metrics

Initial product validation will be measured through:

Number of users adding transactions
Frequency of transaction logging
Interaction with spending visualisations
Qualitative feedback indicating improved awareness of spending behaviour
4. Backend Architecture
Framework

Flask

Chosen for:

Simplicity
Flexibility
Rapid development
Large ecosystem

Flask is sufficient for the initial scale of the application (up to ~7,000 users).

Future Migration

FastAPI

Potential upgrade path to support:

Asynchronous request handling
Higher concurrency
Improved performance
Database Strategy
Development (v1–v4)

SQLite

Advantages:

Lightweight
Zero configuration
Ideal for rapid iteration
Production (v5+)

PostgreSQL

Advantages:

Strong concurrency support
Advanced query capabilities
Production-grade reliability
Scalability for larger datasets
ORM and Database Migrations

ORM: SQLAlchemy

Benefits:

Pythonic interaction with databases
Full SQL control when necessary
Industry-standard ecosystem

Development configuration:

echo=True

This logs generated SQL queries for debugging and learning.

Migrations

Alembic

Used starting from v3 to:

Track schema changes
Maintain versioned database structure
Support smooth transitions between environments
Enable migration from SQLite to PostgreSQL
Security & Privacy

Since financial data is involved, the system must prioritise security.

Key considerations:

Secure authentication and session management
Encrypted communication (HTTPS)
Protection of financial records
Preparation for GDPR compliance
5. Frontend Strategy
Early Versions (v1–v5)

Jinja2 Templates

Reasons:

Native integration with Flask
Rapid development
Minimal complexity
Easier debugging
Future Frontend (v6+)

React

Benefits:

Component-based architecture
Faster client-side rendering
More dynamic dashboards
Scalable UI structure
Data Visualisation

Primary library:

Chart.js

Advantages:

Interactive browser-based charts
Responsive visualisations
Easy integration with Flask via JSON data

Workflow:

Flask → JSON data → Chart.js → Interactive charts

Alternative:

Matplotlib

Used only when static server-generated charts are required.

6. Machine Learning Strategy
Framework

scikit-learn

Chosen because:

Lightweight
Well-tested
Ideal for structured financial data
Easier to interpret than deep learning models
Planned ML Tasks

Transaction Classification

Automatically categorise transactions based on description or merchant.

Spending Forecasting

Use regression models to estimate future spending patterns.

Anomaly Detection

Identify unusual transactions such as:

Unusually large purchases
New merchant categories
Irregular spending behaviour
Rationale

Traditional machine learning methods are sufficient for the expected dataset size.

Deep learning frameworks such as TensorFlow or PyTorch would introduce unnecessary complexity at this stage.

7. Product Roadmap
Version	Backend	Database	Frontend	Key Features
v1	Flask	SQLite	Jinja2	Basic transactions CRUD
v2–v4	Flask	SQLite	Jinja2	UI improvements and analytics
v5	Flask / FastAPI	PostgreSQL	Jinja2	Production database migration
v6+	FastAPI	PostgreSQL	React	Dynamic UI and advanced analytics
8. API Design (MVP)
Method	Endpoint	Purpose
POST	/api/auth/register	Create account
POST	/api/auth/login	Log in
POST	/api/auth/logout	Log out
POST	/api/transactions	Create transaction
GET	/api/transactions	List transactions
GET	/api/transactions/{id}	Retrieve transaction
DELETE	/api/transactions/{id}	Delete transaction

All transaction endpoints require authentication.

9. Database Schema
Transactions Table
Column	Type	Constraints	Purpose
id	Integer	PK, Auto Increment	Unique identifier
amount	Decimal(10,2)	NOT NULL	Transaction value
description	String(255)	NOT NULL	Purchase description
category_id	Integer	FK → categories.id	Category reference
type	String(10)	NOT NULL	income / expense
date	Date	NOT NULL	Transaction date
merchant	String(255)	NULLABLE	Merchant name
is_recurring	Boolean	Default False	Recurring transaction flag
created_at	DateTime	Default now()	Record creation time
updated_at	DateTime	Auto-update	Last modification

Note: Floating point values must never be used for financial amounts.

Categories Table
Column	Type	Constraints	Purpose
id	Integer	PK	Category identifier
name	String(50)	UNIQUE, NOT NULL	Category name
icon	String(10)	NULLABLE	UI icon
colour	String(7)	NULLABLE	Chart colour
Why Normalisation Matters

Instead of storing "Food" repeatedly in transactions:

category_id = 1

This references the categories table.

Benefits:

Consistency
Reduced storage
Easier updates
Budgets Table
Column	Type	Constraints	Purpose
id	Integer	PK	Unique identifier
category_id	Integer	FK → categories.id	Budget category
amount	Decimal(10,2)	NOT NULL	Monthly budget
month	Integer	1–12	Budget month
year	Integer	NOT NULL	Budget year
Anomalies Table
Column	Type	Constraints	Purpose
id	Integer	PK	Unique identifier
transaction_id	Integer	FK → transactions.id	Flagged transaction
reason	String(255)	NOT NULL	Detection explanation
severity	String(10)	NOT NULL	low / medium / high
flagged_at	DateTime	Default now()	Detection timestamp
10. Schema Evolution Plan

Database structure will expand as features evolve.

Version	Tables Introduced	Reason
v1.0	transactions	Basic transaction storage
v2.0	+ categories	Structured categorisation
v3.0	No change	ML training on existing data
v4.0	+ budgets, anomalies	Budgeting and anomaly detection
v5.0	PostgreSQL migration	Production readiness

