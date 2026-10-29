# GitHub integration

Label an issue `agentcollab` and AgentCollab clones the repo, runs the agents on the issue,
and, if the change passes tests, review and security analysis, opens a **draft** pull
request that links back to the run. If it can't produce a passing change, it comments on the
issue instead. PRs are always drafts, so a person decides what gets merged.

## 1. Create the GitHub App

GitHub → Settings → Developer settings → GitHub Apps → **New GitHub App**.

| Field | Value |
|---|---|
| Homepage URL | your AgentCollab URL |
| Webhook URL | `https://<your-server>/api/github/webhook` |
| Webhook secret | a long random string (`openssl rand -hex 32`) |

**Repository permissions:**

| Permission | Access | Why |
|---|---|---|
| Contents | Read & write | clone the repo and push the branch |
| Issues | Read & write | read the issue and comment on it |
| Pull requests | Read & write | open the draft PR |
| Metadata | Read-only | required by GitHub |

**Subscribe to events:** Issues.

Create the app, note its **App ID**, and generate a **private key** (`.pem` file).
Then install the app on the repos it should work on. Start with a playground repo.

## 2. Configure AgentCollab

In `backend/.env`:

```bash
GITHUB_APP_ID=123456
GITHUB_WEBHOOK_SECRET=<the secret from step 1>
# The .pem contents on one line, with newlines written as \n:
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----\n"
AGENTCOLLAB_PUBLIC_URL=https://<your-server>   # for links back to the run
# AGENTCOLLAB_GITHUB_LABEL=agentcollab
```

To turn the key file into one line: `awk 'NF {printf "%s\\n", $0}' key.pem`.

## 3. Try it

1. Create a label named `agentcollab` in the repo.
2. Open an issue that describes a small, testable change.
3. Add the label. A draft PR (or a comment) appears when the run finishes.

To receive webhooks on your own machine while developing, forward them with
[smee.io](https://smee.io): set the app's webhook URL to your smee channel and run
`npx smee-client --url <channel> --target http://localhost:8000/api/github/webhook`.

## Security notes

- Webhooks are rejected unless their HMAC-SHA256 signature matches the secret.
- Only `issues` events where the configured label was just added start a run.
- The installation token is passed to git through environment config, never in command
  arguments or the remote URL, and expires within an hour.
- Issue text is passed to the agents as data; prompts tell them to ignore instructions in it.
  Generated code only runs inside the network-less sandbox.
- Anyone who can label issues in an installed repo can start a run, which costs money.
  Install the app only on repos where you trust the people with triage access.
- The sandbox image has Python and pytest only. Repos whose tests need other packages
  need those baked into `backend/sandbox-image/Dockerfile`.
