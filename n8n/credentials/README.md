# n8n Credentials

This directory is for storing n8n credential export files (optional).

## Credentials Needed

1. **OpenAI API**
   - Type: HTTP Header Auth or OpenAI credential
   - Header: Authorization
   - Value: Bearer YOUR_API_KEY

2. **Google Sheets**
   - Type: Google Sheets OAuth2 or Service Account
   - Use the same service account as configured in `.env`

## Setup in n8n

1. Open n8n at http://localhost:5678
2. Go to Settings → Credentials
3. Add each credential type
4. Reference them in the workflows

## Security

- Never commit actual credential files
- This directory is gitignored except for this README
- Store API keys in environment variables, not in workflow files
