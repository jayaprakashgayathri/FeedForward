# FeedForward

**Food Donation Management System**

FeedForward is a web application that bridges the gap between restaurants and food establishments with surplus food, and charitable organizations, shelters, and community kitchens in need of donations. It streamlines the entire donation lifecycle — from food listing and pickup scheduling to delivery confirmation and impact tracking — and is deployed using modern DevOps practices including containerization and CI/CD pipelines.

> College DevOps Project · 2026

---

## Table of Contents

- [Overview](#overview)
- [Objectives](#objectives)
- [User Roles](#user-roles)
- [Core Modules](#core-modules)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Docker Services](#docker-services)
- [Database Schema](#database-schema)
- [API Endpoints](#api-endpoints)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Overview

Thousands of tons of edible food are wasted daily by restaurants, hotels, and catering services, while millions of people face food insecurity. FeedForward acts as the digital intermediary that connects these two groups efficiently, transparently, and in real time.

## Objectives

- Reduce food waste by enabling restaurants to list surplus food quickly and easily
- Help charities and shelters access food donations in their vicinity
- Demonstrate real-world DevOps practices in a production-grade project
- Track and visualize the social and environmental impact of donations

## User Roles

| Role | Description | Key Actions |
|------|-------------|--------------|
| **Donor** | Restaurants, hotels, catering services | Post food, schedule pickup, view history |
| **Recipient** | NGOs, shelters, orphanages, kitchens | Browse food, claim donations, give feedback |

## Core Modules

### Authentication & User Management
- Role-based registration and login (Donor, Recipient)

### Food Listing Module
- Post available food with name, category, quantity, and expiry time
- Categories: Cooked Meals, Raw Ingredients, Packaged Food
- Real-time expiry countdown timer per listing

### Donation Request Module
- Browse nearby available food listings
- Reserve/claim a listing before it expires
- Automatic request confirmation to donor


## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend | Flask (Python) | Web framework, routing, business logic |
| Templating | Jinja2 | Server-rendered HTML pages |
| ORM | Flask-SQLAlchemy | Database models and queries |
| Database | PostgreSQL (via psycopg2-binary) | Relational data storage |
| Authentication | Flask-Login | Session-based login and user management |
| Containerization | Docker + Docker Compose | Multi-container deployment |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Testing | pytest + pytest-flask | Backend unit/integration tests |
| E2E Testing | Selenium | Automated browser/UI testing |

## Architecture

The DevOps pipeline is structured to demonstrate industry-grade practices including containerization, continuous integration, and automated deployment. The application is containerized with Docker, orchestrated via Docker Compose, and automatically tested and deployed through a GitHub Actions CI/CD pipeline on every push to `main`.

| Stage | Tool | Description |
|-------|------|-------------|
| Version Control | GitHub | Source code management and branching |
| CI/CD Pipeline | GitHub Actions | Auto build, test, and deploy on push |
| Containerization | Docker | Application packaged into a container image |
| Orchestration | Docker Compose | Multi-container coordination (app + database) |
| Database Persistence | Docker Volumes | PostgreSQL data persists on restart |
| Environment Config | ENV Variables | Separate dev and production configs |

## Docker Services

| Container | Base Image | Role |
|-----------|------------|------|
| `app` | Python | Runs the Flask application via Gunicorn |
| `db` | postgres | PostgreSQL database |

## Database Schema

**Core tables:** `users`, `organizations`, `food_listings`, `donation_requests`,

**Key relationships:**
- 1 user → 1 organization
- 1 donor → many food listings
- 1 listing → many donation requests

## API Endpoints

| Method | Endpoint | Description | Role |
|--------|----------|--------------|------|
| POST | `/register` | Register a new user | All |
| POST | `/login` | Log in a user | All |
| GET | `/listings` | Get all available food listings | All |
| POST | `/listings` | Create a new food listing | Donor |
| PATCH | `/listings/:id` | Update a listing status | Donor |
| POST | `/requests` | Submit a donation request | Recipient |
| GET | `/requests/:id` | Get request details | Auth |

## Getting Started

### Prerequisites
- Docker & Docker Compose
- Python 3.10+ (for local, non-containerized development)
- PostgreSQL (if running the database outside Docker)

### Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/jayaprakashgayathri/FeedForward.git
cd FeedForward

# Copy environment templates
cp .env.example .env

# Build and start the app
docker-compose up --build
```

### Local Development (without Docker)

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env

# Run the app
python app.py
```

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
FLASK_APP=app.py
FLASK_ENV=development
SECRET_KEY=your_secret_key
DATABASE_URL=postgresql://user:password@db:5432/feedforward

# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASS=your_password
```

## Roadmap

- [ ] Real-time notifications via WebSockets
- [ ] Mobile app support
- [ ] SMS alerts for low-connectivity regions
- [ ] Multi-language support
- [ ] Advanced analytics dashboard for admins

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please make sure your code passes CI checks before submitting.

<p align="center">Built with dedication to fight food waste and food insecurity.</p>
