# new_testagent2

## Environment setup
Create a `.env` file at the project root with your Azure OpenAI key and endpoint target URI:

```env
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
```

The app will load this key and endpoint automatically on startup.

Optional fallback names are also supported:

```env
# OPENAI_API_KEY=your_azure_openai_key_here
# OPENAI_API_BASE=https://your-resource-name.openai.azure.com/
```

Add simple application users via environment variables (for local/demo use):

```env
# Preferred: use `data/users.json` in project root (takes precedence).
# Example `data/users.json` contents:
# {
#   "alice": "*",
#   "bob": "*",
#   "admin": "*"
# }
#
# Fallback (env): comma-separated username:password pairs
APP_USERS=alice:*,bob:*
# Optional single admin entry (admin has same access as other users)
ADMIN_USER=admin
ADMIN_PASS=*
```
