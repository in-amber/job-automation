# Security

## Boundaries

### Filesystem Access
- Cowork should only access the project root and approved document files
- No access to system directories or other projects

### Browser Isolation
- Use a separate browser profile for job applications
- Do not share sessions with personal browsing

### Account Security
- No autonomous signup in v1 (ever)
- No autonomous credential management
- Manual login only

## Secrets Management

### Environment Variables
- Store all API keys in `.env`
- Never hardcode secrets in repository files
- `.env` is gitignored

### Google Credentials
- Store Google service account JSON in `config/google_credentials.json`
- This file is gitignored

## What We Never Store

- Passwords
- OTP codes
- Full credit card or payment info
- Social Security Numbers

## What We Do Store

- Resume content (for application context)
- Cover letters
- Application form answers (non-sensitive)
- Screenshots of application forms
- Job descriptions and decisions

## Non-Goals (v1)

These are explicitly out of scope:
- Captcha solving
- OTP/email/SMS verification handling
- Multi-factor authentication automation
- Broad permissions on arbitrary domains
