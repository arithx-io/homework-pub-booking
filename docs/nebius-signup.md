# Nebius signup — step by step

You need a Nebius Token Factory API key to run `make verify` and any
`make ex*-real` target. Free tier is more than enough for the whole
homework (~50p of tokens end-to-end if you re-run aggressively).

## 1. Go to the Token Factory

Open [https://tokenfactory.nebius.com](https://tokenfactory.nebius.com)
in a browser.

> **Careful:** Nebius has a separate product called "Nebius AI Studio"
> at studio.nebius.ai. That's NOT what we use. Token Factory is its own
> thing with its own keys.

## 2. Sign up

Use **GitHub OAuth** if possible — it's the fastest, and if your cohort
registered you, the credit will be attached to the email your GitHub
account uses.

## 3. Navigate to API Keys

After login, on the left sidebar: **API Keys** → **Create New Key**.

The key is a long string starting with `eyJ...`. Copy it now — you
CANNOT see it again after you leave the page. If you lose it, revoke
and create a new one.

## 4. Paste into your `.env`

```
# Open .env in your editor, find this line:
NEBIUS_KEY=

# And change it to:
NEBIUS_KEY=eyJhbGciOi... (paste your key here)
```

Save the file.

## 5. Verify

```
make verify
```

The last line should be `✓  All checks passed — ready to start the homework!`.

If the verify step fails with `401 Unauthorized`, check:

- You pasted the full key (they're >100 characters).
- You have no spaces around `=` in the `.env` line.
- You're using Token Factory, not Studio (they have different keys).

## Free tier limits

As of April 2026, Nebius Token Factory free tier gives:

- ~1M free tokens per month for text models (plenty for the homework).
- Rate limit: 60 requests per minute.

If you hit the rate limit during `make ex5-real`, just wait 60 seconds.
If you exhaust the monthly cap, all `ex*-real` runs will start failing
with 429; you can still finish all the offline (`ex5`, `ex6`, `ex7`,
`ex8-text`) targets.

## For cohort students

If your Nebius account was pre-provisioned by your cohort, the instructor
will have sent you credentials separately. In that case, use THOSE
credentials — the free tier key you sign up for won't have the cohort's
bonus credits attached.

## Revoking a key

If you ever suspect a key has leaked (accidental commit, etc.):

1. Go back to the API Keys page.
2. Find the offending key.
3. Click **Revoke**.
4. Create a new key.
5. Update `.env`.

Revocation is immediate. Rotated keys cannot be re-activated.
