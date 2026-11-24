# 🌐 Oracle Cloud Infrastructure (OCI) IaaS Deployment Guide

This guide walks you through deploying **JobRadar AI** on an **Oracle Cloud Always-Free Compute Instance** with automated Docker Compose orchestration, PostgreSQL 16, Redis 7, Celery, Nginx reverse proxy, and automated Let's Encrypt SSL certificates.

---

## 📋 Prerequisites

1. An **Oracle Cloud Infrastructure (OCI)** account ([cloud.oracle.com](https://cloud.oracle.com)).
2. An SSH Key pair (`id_rsa` and `id_rsa.pub`).
3. *(Optional)* A domain name or free dynamic DNS (e.g. from [DuckDNS](https://www.duckdns.org), [Cloudflare](https://cloudflare.com), or [No-IP](https://www.noip.com)).

---

## 🏗 Step 1: Provision Always-Free Compute Instance

1. Navigate to **Compute > Instances > Create Instance** in your OCI Console.
2. **Image and Shape**:
   - **Image**: `Canonical Ubuntu 24.04 Minimal` or `Oracle Linux 9`.
   - **Shape**:
     - *Recommended*: **Ampere A1 (ARM)**: 2 OCPUs, 12 GB RAM (Always Free).
     - *Alternative*: **VM.Standard.E2.1.Micro (AMD)**: 1 OCPU, 1 GB RAM.
3. **Networking**:
   - Select your default Virtual Cloud Network (VCN) and public subnet.
   - Assign a **Public IPv4 address**.
4. **SSH Keys**:
   - Upload your public SSH key (`id_rsa.pub`).
5. Click **Create** and note the **Public IP Address** (e.g., `140.238.xxx.xxx`).

---

## 🛡 Step 2: Open OCI VCN Ingress Rules

By default, OCI blocks all ports except Port 22 (SSH). You must allow HTTP and HTTPS:

1. In the OCI Console, go to **Networking > Virtual Cloud Networks**.
2. Select your VCN > Click on **Default Security List**.
3. Under **Ingress Rules**, click **Add Ingress Rules**:
   - **Rule 1 (HTTP)**:
     - Source CIDR: `0.0.0.0/0`
     - IP Protocol: `TCP`
     - Destination Port Range: `80`
     - Description: `Allow HTTP traffic for Nginx & Let's Encrypt`
   - **Rule 2 (HTTPS)**:
     - Source CIDR: `0.0.0.0/0`
     - IP Protocol: `TCP`
     - Destination Port Range: `443`
     - Description: `Allow HTTPS traffic for Nginx SSL`
4. Click **Add Ingress Rules**.

---

## 💻 Step 3: Connect and Bootstrap the VM

Connect via SSH to your VM:

```bash
ssh -i /path/to/private_key ubuntu@<YOUR_OCI_PUBLIC_IP>
```

Clone the repository:

```bash
git clone https://github.com/visitacionmaquee/telegram-job-bot.git
cd telegram-job-bot
```

Run the automated OCI bootstrap script:

```bash
chmod +x deploy/setup_oci_vm.sh deploy/init_ssl.sh
bash deploy/setup_oci_vm.sh
```

> **Note**: `setup_oci_vm.sh` automatically updates system packages, configures OS-level iptables rules (essential for OCI), installs Docker with the Compose plugin, and registers a `systemd` service (`jobradar.service`) to ensure the entire stack auto-restarts if the VM reboots.

---

## 🔑 Step 4: Configure Production Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
nano .env
```

Set your production credentials:
- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot API token.
- `TELEGRAM_USER_ID`: Your personal Telegram ID (`8880104517`).
- `POSTGRES_PASSWORD`: A secure random password for PostgreSQL.
- `GEMINI_API_KEY`: *(Optional)* Your Google Gemini API key.

---

## 🚀 Step 5: Launch the Production Stack

Start all containers in detached mode:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Verify that all services are running and healthy:

```bash
docker compose -f docker-compose.prod.yml ps
```

You should see:
- `jobradar_db` (Postgres 16, healthy)
- `jobradar_redis` (Redis 7, healthy)
- `jobradar_api` (FastAPI backend, healthy)
- `jobradar_worker` (Celery background worker)
- `jobradar_bot` (Telegram Bot polling engine)
- `jobradar_nginx` (Nginx reverse proxy, ports 80/443)
- `jobradar_certbot` (Automated SSL renewer)

---

## 🔒 Step 6: Provision Free Let's Encrypt SSL Certificate

Point your domain (or free DuckDNS subdomain) to your OCI VM's Public IP address in your DNS manager (A Record).

Then execute the SSL initializer:

```bash
bash deploy/init_ssl.sh yourdomain.com your-email@example.com
```

The script will:
1. Initialize temporary certificates so Nginx starts cleanly.
2. Complete the Let's Encrypt HTTP-01 ACME challenge.
3. Install 4096-bit RSA SSL certificates.
4. Reload Nginx with strict HTTPS, TLS 1.2/1.3, and HSTS headers.

---

## 🌟 Step 7: Access Your Live SaaS Application

Open your browser and navigate to:
- **Web Dashboard**: `https://yourdomain.com/dashboard`
- **Swagger REST API**: `https://yourdomain.com/docs`
- **Health Check**: `https://yourdomain.com/health`

---

## 🔄 Maintenance & Monitoring

- **View Live Logs**:
  ```bash
  docker compose -f docker-compose.prod.yml logs -f api
  docker compose -f docker-compose.prod.yml logs -f worker
  docker compose -f docker-compose.prod.yml logs -f nginx
  ```
- **Update Application After Git Push**:
  ```bash
  git pull origin main
  docker compose -f docker-compose.prod.yml up -d --build
  ```
- **Systemd Auto-Restart Status**:
  ```bash
  sudo systemctl status jobradar.service
  ```
