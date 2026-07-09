# PSEG New Jersey Automation Addon

This Home Assistant addon provides automated login services for PSEG New Jersey using Playwright. It runs in its own container and exposes a web API for cookie generation.

**Version**: 2.4.5

## Features

- 🚀 **Automated Login**: Uses Playwright to handle reCAPTCHA and login
- 🔐 **Cookie Generation**: Returns fresh authentication cookies
- 🌐 **Web API**: Simple HTTP endpoints for integration use
- 🐳 **Docker-based**: Runs in isolated container with all dependencies
- 📱 **Home Assistant Integration**: Works seamlessly with PSEG New Jersey integration

## Installation

### **Option 1: Repository Installation (Recommended)**

1. **Add the custom repository:**

   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click the three dots menu (⋮) → **Repositories**
   - Add: `https://github.com/daswass/ha-psegli`
   - Click **Add**

2. **Install the addon:**
   - Find **PSEG New Jersey Automation** in the store
   - Click **Install**
   - Wait for installation to complete
   - Click **Start**

### **Option 2: Local Installation**

1. **Copy to Addons Directory**: Copy this folder to your Home Assistant `addons` directory
2. **Install Addon**: Go to Settings → Add-ons → Add-on Store → Local Add-ons
3. **Start Addon**: Click "Install" then "Start"

## API Endpoints

### Health Check

```
GET /health
```

### Login (JSON)

```
POST /login
Content-Type: application/json

{
  "username": "your_email@example.com",
  "password": "your_password"
}
```

### Login (Form Data)

```
POST /login-form
Content-Type: application/x-www-form-urlencoded

username=your_email@example.com&password=your_password
```

## Response Format

```json
{
  "success": true,
  "cookies": {
    "ASP.NET_SessionId": "abc123...",
    "__RequestVerificationToken": "xyz789...",
    "other_cookies": "..."
  }
}
```

## Integration Usage

The PSEG New Jersey integration will automatically use this addon when available. No additional configuration needed.

## Multi-Factor Authentication (MFA)

PSEG New Jersey added MFA in late 2024/early 2025. When MFA is required:

1. **POST /login** with username and password - the addon will return `mfa_required: true`
2. Check your email or phone for the verification code (sent by PSEG)
3. **POST /login/mfa** with `{"code": "123456"}` (your code) - the addon completes login and returns cookies

The addon keeps the browser session alive for a few minutes after step 1, so complete step 3 promptly.

## Troubleshooting

- **Port Conflicts**: Ensure port 8000 is available
- **Browser Issues**: Check addon logs for Playwright errors
- **Network Issues**: Verify addon can reach PSEG website
- **MFA Required**: If login fails with "still on login page", PSEG now requires MFA - use the two-step flow above

## Development

To build locally:

```bash
docker build -t psegli-automation .
docker run -p 8000:8000 psegli-automation
```

### Watch MFA flow in headed mode (visible browser)

To see the browser during login/MFA for debugging, run the addon locally (not in Docker/HA) with headed mode:

```bash
cd addons/psegli-automation
HEADED=1 python run.py
```

Then in another terminal:
1. `curl -X POST http://localhost:8000/login -H "Content-Type: application/json" -d '{"username":"your@email.com","password":"yourpass"}'`
2. When you get the SMS code, `curl -X POST http://localhost:8000/login/mfa -H "Content-Type: application/json" -d '{"code":"123456"}'`

A browser window will open so you can watch the MFA flow.
