# Kindred Beta Deployment Guide

Step-by-step instructions to get Kindred running on a live server for beta testing.

**Estimated cost: ~$5-7/month** | **Time to deploy: ~30 minutes**

---

## What You Need to Get

| Item | Where | Cost | Notes |
|------|-------|------|-------|
| **VPS** | [Hetzner](https://hetzner.cloud) | ~$4.35/mo | CX22: 2 vCPU, 4GB RAM, 40GB disk. Pick the datacenter closest to your users. |
| **Domain** | [Cloudflare Registrar](https://dash.cloudflare.com) | ~$10/yr | Cheapest .com registrar. Any registrar works. |
| **Email sending** | [Resend](https://resend.com) or [Brevo](https://brevo.com) | $0 | Resend: 100 emails/day free. Brevo: 300/day free. |
| **DNS** | [Cloudflare](https://cloudflare.com) (free tier) | $0 | Free DNS + CDN + DDoS protection. |

**Total: ~$5.18/month + $10/year for domain**

### Alternatives

| VPS alternatives | Cost | Notes |
|-----------------|------|-------|
| [Oracle Cloud](https://cloud.oracle.com) | **$0** (free tier) | ARM A1: 4 vCPU, 24GB RAM. Hard to get capacity. |
| [DigitalOcean](https://digitalocean.com) | $6/mo | $200 free credit for 60 days with referral. |
| [Vultr](https://vultr.com) | $5/mo | Good global coverage. |
| [Linode/Akamai](https://linode.com) | $5/mo | $100 free credit for 60 days. |

---

## Step 1: VPS Setup

### 1.1 Create the server

1. Sign up at [Hetzner Cloud](https://hetzner.cloud)
2. Create a new project
3. Add a server:
   - **Image**: Ubuntu 24.04
   - **Type**: CX22 (2 vCPU, 4GB RAM)
   - **Location**: closest to your users
   - **SSH Key**: add your public key (or create one with `ssh-keygen -t ed25519`)
   - **Name**: `kindred`
4. Note the server IP address

### 1.2 Point your domain

In your DNS provider (Cloudflare recommended):

| Type | Name | Content | Proxy |
|------|------|---------|-------|
| A | `@` | `YOUR_SERVER_IP` | DNS only (gray cloud) |
| A | `www` | `YOUR_SERVER_IP` | DNS only (gray cloud) |

**Important**: Keep the Cloudflare proxy OFF (gray cloud) so Caddy can get SSL certificates. You can enable it later if you want Cloudflare's CDN, but then you'd need to configure Caddy differently.

### 1.3 Initial server hardening

SSH into your server and run:

```bash
ssh root@YOUR_SERVER_IP
```

```bash
# Update system
apt update && apt upgrade -y

# Create kindred user (no root for running the app)
useradd -m -s /bin/bash kindred

# Firewall - only allow SSH, HTTP, HTTPS
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw --force enable

# Disable root password login (SSH key only)
sed -i 's/#PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
sed -i 's/PermitRootLogin yes/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config
systemctl reload ssh
```

---

## Step 2: Install Dependencies

Still as root on the server:

```bash
# Python 3.12+
apt install -y python3 python3-venv python3-pip git sqlite3 curl

# Caddy (auto-HTTPS reverse proxy)
apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | tee /etc/apt/sources.list.d/caddy-stable.list
apt update
apt install -y caddy
```

---

## Step 3: Deploy Kindred

```bash
# Clone the repo
git clone https://github.com/SysAdminDoc/kindred.git /opt/kindred
chown -R kindred:kindred /opt/kindred
cd /opt/kindred

# Create virtual environment and install deps
sudo -u kindred python3 -m venv .venv
sudo -u kindred .venv/bin/pip install -r requirements.txt

# Create required directories
sudo -u kindred mkdir -p uploads backups
```

---

## Step 4: Configure

### 4.1 Generate secrets

```bash
# Generate JWT secret
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate VAPID keys for push notifications
sudo -u kindred .venv/bin/python deploy/gen-vapid-keys.py
```

### 4.2 Create .env file

```bash
cp deploy/.env.production /opt/kindred/.env
nano /opt/kindred/.env
```

Fill in every value marked `CHANGE_ME` and `REQUIRED`:
- Paste your generated JWT secret
- Set a strong admin password
- Set your domain in `KINDRED_CORS_ORIGINS` (e.g., `https://kindred.app`)
- Uncomment and fill in one email provider block (Resend recommended)
- Paste VAPID keys from step 4.1
- Set `KINDRED_VAPID_CONTACT` to your email

### 4.3 Test it starts

```bash
# Quick test (Ctrl+C to stop)
sudo -u kindred bash -c 'cd /opt/kindred && source .venv/bin/activate && source .env && uvicorn app.main:app --host 127.0.0.1 --port 8000'
```

You should see Uvicorn start without errors. Ctrl+C to stop.

---

## Step 5: Set Up Caddy (HTTPS)

### 5.1 Configure Caddy

```bash
# Copy the Caddyfile
cp /opt/kindred/deploy/Caddyfile /etc/caddy/Caddyfile

# Replace YOUR_DOMAIN with your actual domain
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' /etc/caddy/Caddyfile

# Create log directory
mkdir -p /var/log/caddy

# Reload Caddy
systemctl reload caddy
```

Caddy automatically gets SSL certificates from Let's Encrypt. No configuration needed.

### 5.2 Verify SSL

After a minute, visit `https://yourdomain.com`. You should see a certificate error (since Kindred isn't running yet), but the SSL lock should appear. That means Caddy is working.

---

## Step 6: Set Up Systemd Services

```bash
# Install service files
cp /opt/kindred/deploy/kindred-user.service /etc/systemd/system/
cp /opt/kindred/deploy/kindred-admin.service /etc/systemd/system/

# Reload systemd
systemctl daemon-reload

# Enable services (auto-start on boot)
systemctl enable kindred-user kindred-admin

# Start services
systemctl start kindred-user kindred-admin

# Check they're running
systemctl status kindred-user
systemctl status kindred-admin
```

---

## Step 7: Verify Everything Works

```bash
# Check health endpoint
curl -s https://yourdomain.com/api/health | python3 -m json.tool

# Check admin endpoint (through Caddy)
curl -s https://yourdomain.com/api/admin/health | python3 -m json.tool

# Check logs for errors
journalctl -u kindred-user --no-pager -n 20
journalctl -u kindred-admin --no-pager -n 20

# Check Caddy logs
tail -20 /var/log/caddy/kindred-access.log
```

Visit:
- **User portal**: `https://yourdomain.com`
- **Admin portal**: `https://yourdomain.com/admin`

Log into admin with the credentials you set in `.env`.

**Immediately change the admin password** through the admin portal after first login.

---

## Step 8: Set Up Backups

### Option A: Local backups with offsite rsync (recommended)

```bash
# Make backup script executable
chmod +x /opt/kindred/deploy/backup-offsite.sh

# Add to root's crontab (runs daily at 3 AM)
crontab -e
```

Add this line:

```
0 3 * * * KINDRED_DIR=/opt/kindred /opt/kindred/deploy/backup-offsite.sh >> /var/log/kindred-backup.log 2>&1
```

For offsite backups, set `BACKUP_REMOTE` in the crontab line:

```
0 3 * * * KINDRED_DIR=/opt/kindred BACKUP_REMOTE=user@backupbox:/backups/kindred/ /opt/kindred/deploy/backup-offsite.sh >> /var/log/kindred-backup.log 2>&1
```

### Option B: Just rely on Kindred's built-in backups

The app already runs automatic backups every 12 hours (configurable in `.env`). These stay on the same server though, so not a true backup.

---

## Step 9: Beta Label

The app is now live. Since this is a beta:

1. Log into the admin portal
2. Go to **Announcements**
3. Create an announcement:
   - **Message**: "Welcome to the Kindred beta! Things may break. Report issues to [your contact]."
   - **Type**: info
4. This will show as a dismissible banner to all users

---

## Docker Alternative

If you prefer Docker over systemd:

```bash
cd /opt/kindred

# Copy and configure
cp deploy/.env.production .env
nano .env  # fill in your values

# Edit the Docker Caddyfile
cp deploy/Caddyfile.docker deploy/Caddyfile
sed -i 's/YOUR_DOMAIN/yourdomain.com/g' deploy/Caddyfile

# Launch
cd deploy
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

---

## Email Provider Setup

### Resend (recommended - simplest)

1. Sign up at [resend.com](https://resend.com)
2. Add and verify your domain (they walk you through DNS records)
3. Create an API key
4. In `.env`:
   ```
   KINDRED_SMTP_HOST=smtp.resend.com
   KINDRED_SMTP_PORT=587
   KINDRED_SMTP_USER=resend
   KINDRED_SMTP_PASSWORD=re_YOUR_API_KEY_HERE
   KINDRED_SMTP_FROM=noreply@yourdomain.com
   ```
5. Restart services: `systemctl restart kindred-user kindred-admin`

### Brevo (higher free limit)

1. Sign up at [brevo.com](https://brevo.com)
2. Go to SMTP & API > SMTP
3. Create SMTP credentials
4. In `.env`:
   ```
   KINDRED_SMTP_HOST=smtp-relay.brevo.com
   KINDRED_SMTP_PORT=587
   KINDRED_SMTP_USER=your-brevo-login-email
   KINDRED_SMTP_PASSWORD=your-smtp-key
   KINDRED_SMTP_FROM=noreply@yourdomain.com
   ```
5. Restart services: `systemctl restart kindred-user kindred-admin`

---

## Ongoing Maintenance

### View logs
```bash
journalctl -u kindred-user -f         # live user server logs
journalctl -u kindred-admin -f        # live admin server logs
tail -f /var/log/caddy/kindred-access.log  # HTTP access logs
```

### Restart after code changes
```bash
cd /opt/kindred
sudo -u kindred git pull
systemctl restart kindred-user kindred-admin
```

### Update system
```bash
apt update && apt upgrade -y
# Reboot if kernel was updated
```

### Monitor disk usage
```bash
df -h                                          # disk space
du -sh /opt/kindred/uploads/                   # upload folder size
du -sh /opt/kindred/kindred.db                 # database size
du -sh /opt/kindred/backups/                   # backup folder size
```

### Database maintenance
The app runs SQLite VACUUM automatically every 7 days. You can also trigger it manually from the admin dashboard under the Operations tab.

---

## Troubleshooting

### Caddy won't get SSL certificate
- Ensure DNS A record points to your server IP
- Ensure Cloudflare proxy is OFF (gray cloud, not orange)
- Ensure ports 80 and 443 are open: `ufw status`
- Check Caddy logs: `journalctl -u caddy -f`

### Services won't start
```bash
# Check what's wrong
journalctl -u kindred-user -n 50 --no-pager
# Common: .env file not readable by kindred user
chown kindred:kindred /opt/kindred/.env
chmod 600 /opt/kindred/.env
```

### WebSocket connections failing
- Caddy handles WebSocket upgrade automatically
- If using Cloudflare proxy (orange cloud), WebSockets are supported on all plans
- Check browser console for connection errors

### Database locked errors
- SQLite WAL mode handles most concurrency. If you see locking under load, it's time to consider PostgreSQL migration.

### Emails not sending
```bash
# Test SMTP manually
python3 -c "
import smtplib
s = smtplib.SMTP('YOUR_SMTP_HOST', 587)
s.starttls()
s.login('YOUR_USER', 'YOUR_PASSWORD')
s.sendmail('from@test.com', 'your@email.com', 'Subject: Test\n\nIt works!')
s.quit()
print('OK')
"
```

### Out of disk space
```bash
# Find large files
du -sh /opt/kindred/uploads/* | sort -rh | head -20
# Clean old backups
find /opt/kindred/backups -name "*.db*" -mtime +7 -delete
# Vacuum database
sqlite3 /opt/kindred/kindred.db "VACUUM;"
```

---

## Security Checklist

Before sharing the beta URL:

- [ ] Changed default admin password
- [ ] Set a strong JWT secret (not the default)
- [ ] CORS set to your domain only (not `*`)
- [ ] Firewall active (only 22, 80, 443 open)
- [ ] SSH key auth only (no password login)
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] Admin portal only accessible via `/admin` (not on a separate port externally)
- [ ] Tested email delivery works (register a test account)
- [ ] Backups running (check `/opt/kindred/backups/`)
- [ ] Checked `https://yourdomain.com` shows valid SSL
