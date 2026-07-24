# FeedForward

**Food Donation Management System**

FeedForward is a full-stack web application that bridges the gap between restaurants and food establishments with surplus food, and charitable organizations, shelters, and community kitchens in need of donations. It streamlines the entire donation lifecycle — from food listing and pickup scheduling to delivery confirmation and impact tracking — and is deployed using modern DevOps practices including containerization, CI/CD pipelines, and cloud infrastructure.

> College DevOps Project · 2026

---

## Table of Contents

- [Overview](#-overview)
- [Objectives](#-objectives)
- [User Roles](#-user-roles)
- [Core Modules](#-core-modules)
- [Tech Stack](#-tech-stack)
- [Architecture](#-architecture)
- [Docker Services](#-docker-services)
- [Database Schema](#-database-schema)
- [API Endpoints](#-api-endpoints)
- [Getting Started](#-getting-started)
- [Environment Variables](#-environment-variables)
- [Roadmap](#-roadmap)
- [Contributing](#-contributing)

---

## Overview

Thousands of tons of edible food are wasted daily by restaurants, hotels, and catering services, while millions of people face food insecurity. FeedForward acts as the digital intermediary that connects these two groups efficiently, transparently, and in real time.

## Objectives

- Reduce food waste by enabling restaurants to list surplus food quickly and easily
- Help charities and shelters access food donations in their vicinity
- Coordinate volunteers for efficient pickup and delivery logistics
- Provide admins with full visibility and control over the donation pipeline
- Demonstrate real-world DevOps practices in a production-grade project
- Track and visualize the social and environmental impact of donations

## User Roles

| Role | Description | Key Actions |
|------|-------------|--------------|
| **Donor** | Restaurants, hotels, catering services | Post food, schedule pickup, view history |
| **Recipient** | NGOs, shelters, orphanages, kitchens | Browse food, claim donations, give feedback |
| **Volunteer** | Individuals helping with logistics | Accept delivery tasks, confirm handoffs |
| **Admin** | System administrators | Manage users, monitor donations, reports |

## Core Modules

### Authentication & User Management
- Role-based registration and login (Donor, Recipient, Volunteer, Admin)
- JWT-based authentication with refresh tokens
- Profile management with organization details
- Email verification on signup

### Food Listing Module
- Post available food with name, category, quantity, and expiry time
- Categories: Cooked Meals, Raw Ingredients, Packaged Food, Beverages, Bakery
- Real-time expiry countdown timer per listing
- Auto-expiry when time runs out
- Image upload support

### Donation Request Module
- Browse nearby available food listings
- Filter by food type, distance, dietary type (veg/non-veg), and quantity
- Reserve/claim a listing before it expires
- Automatic request confirmation to donor

### Volunteer & Logistics Module
- Available pickups surfaced on volunteer dashboard
- Accept and manage delivery tasks
- QR code-based handoff confirmation at pickup and dropoff
- Route display via Leaflet.js maps integration

### Admin Dashboard
- Overview of active, completed, and expired donations
- User management: approve, suspend, delete accounts
- Impact reports: meals saved, food weight, CO₂ reduced
- Notification and alert management

### Notification System
- Email notifications for donation status updates
- In-app alerts for new listings near recipients
- Expiry warning alerts for donors

### Impact Tracker
- Total meals donated per donor
- Total food weight saved from waste
- Leaderboard of top donors and volunteers

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| UI/UX Design | Figma | Wireframes and design prototypes |
| Frontend | React + Tailwind CSS | User interface and interactions |
| Backend | Express.js (Node.js) | REST API and business logic |
| Database | PostgreSQL | Relational data storage |
| Authentication | JWT + bcrypt | Secure login and sessions |
| Containerization | Docker + Docker Compose | Multi-container deployment |
| CI/CD | GitHub Actions | Automated testing and deployment |
| Hosting | Render / Railway | Free-tier cloud hosting |
| Maps | Leaflet.js | Location and routing display |
| Email | Nodemailer | Notification emails |

## Architecture

The DevOps pipeline is structured to demonstrate industry-grade practices including containerization, continuous integration, and automated deployment. Each service is isolated in its own Docker container, orchestrated via Docker Compose, and automatically deployed through a GitHub Actions CI/CD pipeline on every push to `main`.

| Stage | Tool | Description |
|-------|------|-------------|
| Version Control | GitHub | Source code management and branching |
| CI/CD Pipeline | GitHub Actions | Auto build, test, and deploy on push |
| Containerization | Docker | Each service in its own container |
| Orchestration | Docker Compose | Multi-container coordination |
| Container Registry | Docker Hub | Store and distribute Docker images |
| Reverse Proxy | Nginx | Route traffic to frontend and backend |
| Database Persistence | Docker Volumes | PostgreSQL data persists on restart |
| Environment Config | ENV Variables | Separate dev and production configs |
| Monitoring | Prometheus + Grafana | App health metrics and dashboards |
| Hosting | Render / Railway | Free cloud deployment platform |

## Docker Services

| Container | Base Image | Port | Role |
|-----------|------------|------|------|
| `frontend` | `node:alpine` | 3000 | Serves the React application |
| `backend` | `node:alpine` | 8000 | Runs the Express.js REST API |
| `db` | `postgres:15` | 5432 | PostgreSQL database |
| `nginx` | `nginx:alpine` | 80 | Reverse proxy and load balancer |
| `redis` | `redis:alpine` | 6379 | Session caching (optional) |

## Database Schema

**Core tables:** `users`, `organizations`, `food_listings`, `donation_requests`, `deliveries`, `feedback`, `notifications`, `impact_logs`

**Key relationships:**
- 1 user → 1 organization
- 1 donor → many food listings
- 1 listing → many donation requests
- 1 request → 1 delivery
- 1 volunteer → many deliveries
- 1 request → 1 feedback entry
- 1 user → many notifications
- 1 listing → 1 impact log

> See [`docs/database-schema.md`](docs/database-schema.md) for full column-level table definitions (types, keys, constraints).

## API Endpoints

| Method | Endpoint | Description | Role |
|--------|----------|--------------|------|
| POST | `/api/auth/register` | Register a new user | All |
| POST | `/api/auth/login` | Login and get JWT token | All |
| GET | `/api/listings` | Get all available food listings | All |
| POST | `/api/listings` | Create a new food listing | Donor |
| PATCH | `/api/listings/:id` | Update a listing status | Donor |
| POST | `/api/requests` | Submit a donation request | Recipient |
| GET | `/api/requests/:id` | Get request details | Auth |
| POST | `/api/deliveries` | Assign volunteer to delivery | Volunteer |
| PATCH | `/api/deliveries/:id` | Update delivery status | Volunteer |
| POST | `/api/feedback` | Submit donation feedback | Recipient |

## Getting Started

### Prerequisites
- [Docker](https://www.docker.com/) & Docker Compose
- Node.js 18+ (for local, non-containerized development)
- PostgreSQL 15 (if running the DB outside Docker)

### Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/<your-username>/feedforward.git
cd feedforward

# Copy environment templates
cp .env.example .env

# Build and start all services
docker-compose up --build
```

### Local Development (without Docker)

```bash
# Backend
cd backend
npm install
npm run dev

# Frontend
cd frontend
npm install
npm run dev
```

## Environment Variables

Create a `.env` file in the project root (see `.env.example`):

```env
# Backend
PORT=8000
DATABASE_URL=postgresql://user:password@db:5432/feedforward
JWT_SECRET=your_jwt_secret
JWT_REFRESH_SECRET=your_refresh_secret

# Email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=your_email
SMTP_PASS=your_password

# Frontend
VITE_API_BASE_URL=http://localhost:8000
VITE_MAP_TILE_URL=https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png
```

## 🗺 Roadmap

- [ ] Real-time notifications via WebSockets
- [ ] Mobile app (React Native)
- [ ] SMS alerts for low-connectivity regions
- [ ] Multi-language support
- [ ] Advanced analytics dashboard for admins

## 🤝 Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add some feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please make sure your code passes CI checks before submitting.

<p align="center">Built with ❤️ to fight food waste and food insecurity.</p>
