# AlgoGators Update Tool — First-Time Setup

## What you'll need

A **GitHub Personal Access Token (PAT)** — a password that lets the tool upload files to GitHub on your behalf. You generate this once on the GitHub website, paste it into the tool, and you're done.

---

## Step 1 — Generate a Personal Access Token

1. Go to [github.com](https://github.com) and sign in with the **AlgoGators account**.
2. Click your profile picture in the top-right corner, then click **Settings**.
3. In the left sidebar, scroll all the way down and click **Developer settings**.
4. Click **Personal access tokens** → **Tokens (classic)**.
5. Click **Generate new token** → **Generate new token (classic)**.
6. In the **Note** field, type something like `Update Tool` so you remember what it's for.
7. Set **Expiration** — 90 days is a safe default. You'll be asked to make a new token when it expires.
8. Under **Select scopes**, check the box next to **repo** (it's near the top of the list).
9. Scroll to the bottom and click **Generate token**.
10. **Copy the token immediately** — GitHub only shows it once. It looks like `ghp_xxxxxxxxxxxxxxxxxxxx`.

---

## Step 2 — Run the tool for the first time

1. Double-click **Update.exe** (or run `python update_tool.py` if using the source version).
2. The **GitHub Setup** screen appears automatically on first launch.
3. Fill in the three fields:
   - **Personal Access Token** — paste the `ghp_...` token you just copied. The field shows dots for security, that's normal.
   - **GitHub Owner / Org** — type `AlgoGators` (the name of the GitHub organization).
   - **Repository Name** — type the exact repository name, e.g. `algogators-website`.
4. Click **Save & Continue**.

The tool saves your settings to a file called `config.json` in the same folder as the exe. The setup screen won't appear again after that.

---

## Step 3 — Use the tool normally

- Click **Add Research** or **Add Headshot**, fill in the details, then click **Save**.
- Click **Push to Internet** to publish your changes live. This may take a few seconds.
- A pop-up confirms when it's live.

---

## Updating your token or repo settings

Click the small **⚙ Settings** button at the bottom of the home screen at any time to change your token, org name, or repo name.

---

## My token expired — what do I do?

If a push fails with a `401` or "Bad credentials" error, your token has expired. Repeat Step 1 to generate a new one, then open **⚙ Settings** in the tool, clear the token field, paste the new one, and click **Save & Continue**.
