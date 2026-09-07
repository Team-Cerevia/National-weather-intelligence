# AWS EC2 Single-Instance Deployment Guide (METEORA Prototype)

This step-by-step guide deploys the complete **METEORA** stack (PostgreSQL + PostGIS, Redis, FastAPI Backend, Next.js Frontend) on a single **AWS EC2 instance** using Docker Compose.

---

## 1. Launch AWS EC2 Instance

1. Open **AWS Management Console** → **EC2** → **Launch Instance**.
2. **Name**: `METEORA-Prototype`
3. **OS Image**: `Ubuntu Server 24.04 LTS` (64-bit x86)
4. **Instance Type**: `t3.medium` (2 vCPU, 4GB RAM) or `t3.large` (recommended for smooth ONNX ML inference).
5. **Key Pair**: Select or create a key pair (`meteora-key.pem`).
6. **Network Settings (Security Group Rules)**:
   - Allow **SSH (Port 22)** from `My IP` or `0.0.0.0/0`.
   - Allow **HTTP (Port 80)** from `0.0.0.0/0`.
   - Allow **Custom TCP (Port 3000)** for Next.js Frontend from `0.0.0.0/0`.
   - Allow **Custom TCP (Port 8000)** for FastAPI Backend from `0.0.0.0/0`.
7. **Storage**: `30 GB gp3`.

---

## 2. Connect & Setup EC2 Environment

Run the following commands on your local terminal to SSH into EC2 (replace `YOUR_EC2_PUBLIC_IP`):

```bash
# Set key permissions
chmod 400 meteora-key.pem

# SSH into EC2 instance
ssh -i "meteora-key.pem" ubuntu@YOUR_EC2_PUBLIC_IP
```

Once inside EC2, run this 1-liner to install Docker & Docker Compose:

```bash
# Update system & install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
newgrp docker
```

---

## 3. Deploy METEORA via Docker Compose

```bash
# Clone the repository
git clone https://github.com/Team-Cerevia/National-weather-intelligence.git
cd National-weather-intelligence

# Build and start all 4 containers (PostGIS, Redis, Backend, Frontend)
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 4. Verify Live Prototype URL

Once deployed, your live deployment links will be immediately accessible:

- 🎨 **Frontend Command Center UI**: `http://YOUR_EC2_PUBLIC_IP:3000`
- ⚙️ **FastAPI Backend Swagger Docs**: `http://YOUR_EC2_PUBLIC_IP:8000/docs`
- 🩺 **Health Check**: `http://YOUR_EC2_PUBLIC_IP:8000/health`

---

## 5. Useful Management Commands

```bash
# View live container logs
docker compose -f docker-compose.prod.yml logs -f

# Check container status
docker compose -f docker-compose.prod.yml ps

# Restart backend service
docker compose -f docker-compose.prod.yml restart backend
```
