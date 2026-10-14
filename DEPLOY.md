# Deploy your agent to your UQCloud zone

Your zone runs your agent from GitHub and gives it a public HTTPS address,
which the Orchestrator calls at the Week 12 Showcase. There is no Docker on the
zone: you log in, save your API key, and run `sudo mcp-deploy`.

You will need:

- your zone, listed on [coursemgr](https://coursemgr.uqcloud.net/reit7820) as `reit7820-xxxxxxxx`
- your UQ username and password
- your agent's GitHub repo, pushed, with the code you want running on its **default branch**
- a working `ANTHROPIC_API_KEY` (the one in your `.env`)

Two addresses, easy to mix up:

| What | Address |
|---|---|
| Log in with ssh | `reit7820-xxxxxxxx.zones.eait.uq.edu.au` |
| Your agent on the web | `https://reit7820-xxxxxxxx.uqcloud.net/mcp` |

## 1. Check your repo is ready

This repo is already set up. If you started from an older copy, check both:

- **`mcp-agent.toml`** at the top of the repo tells the zone how to run your agent:

  ```toml
  start = "src/agents/charging.py"
  dependencies = "src/pyproject.toml"
  writable = ["src/.cache/", "src/usage.jsonl"]
  ```

  `start` is your agent's file. `writable` lists everything your agent writes
  while it runs. The agent cannot write anywhere else on the zone.

- **The agent listens on `127.0.0.1`**, not `0.0.0.0`. The last line of your
  agent file's `mcp.run(` line passes `host=os.environ.get("HOST", "127.0.0.1")`. Docker sets
  `HOST=0.0.0.0` in `compose.yml`, so your laptop setup keeps working.

Set `AGENT_NAME` and `VERSION` in your agent file, then commit and push. Only
what is on GitHub is deployed, and only from the default branch.

## 2. Check your zone is up

Open `https://reit7820-xxxxxxxx.uqcloud.net/mcp` in a browser. A plain
**401 Authorization Required** page is correct: the zone is running and wants a
token.

## 3. Log in

```bash
ssh <uq-username>@reit7820-xxxxxxxx.zones.eait.uq.edu.au
```

Nothing shows while you type your password. That is normal. Type it and press Enter.

## 4. Save your API key

```bash
sudo mcp-env set ANTHROPIC_API_KEY
sudo mcp-env list                     # shows names only
```

`set` asks for the value, so the key never lands in your shell history. On a
Mac you can copy it from `.env` without printing it, in a terminal on your
laptop:

```bash
grep '^ANTHROPIC_API_KEY=' .env | cut -d= -f2- | tr -d '\n' | pbcopy
```

`LLM_MODEL` is optional (`sudo mcp-env set LLM_MODEL`). W&B keys are not
needed on the zone.

## 5. Give your zone read access to your repo

```bash
sudo mcp-deploy --keygen
```

It prints one line starting with `ssh-ed25519`. That line is safe to share.
If it says **Not trusting it**, stop and ask your tutor.

- **Repo in the course organisation:** paste the line into the setup form and
  choose **Deploy key**. Wait for confirmation that it was added.
- **Repo in your own account:** on GitHub open the repo > Settings > Deploy
  keys > Add deploy key. Paste the line and leave **Allow write access** unticked.

A key can be added to one repo only. Check which repo it reached:

```bash
sudo ssh -i /root/.ssh/mcp-deploy_ed25519 -o IdentitiesOnly=yes -T git@github.com
```

It answers `Hi <owner>/<repo>! You've successfully authenticated`. That must
be the repo you are about to deploy.

## 6. Deploy

Use the SSH address, starting `git@github.com:`, not `https://`:

```bash
sudo mcp-deploy git@github.com:<owner>/<repo>.git
systemctl status mcp-agent            # look for: active (running)
```

A deploy that worked ends like this, with your own agent name:

```
Deployed    : dfe36cd ...
Runtime     : Python (mcp-agent.toml), service runs: python src/agents/charging.py
Public URL  : https://reit7820-xxxxxxxx.uqcloud.net/mcp
Local check : OK, http://127.0.0.1:8000/mcp answered initialize: smac-charging-nearest 1.0.0 (protocol 2025-11-25)
```

If it says it rolled back, the lines above that message say why. The usual
cause on a first deploy is the API key: see Troubleshooting.

After the first deploy that succeeds, `sudo mcp-deploy` on its own pulls your
latest commit. Until then, give it the full address every time.
If a deploy fails, the previous version keeps running.

## 7. Test it from your laptop

The handshake test needs its own virtual environment on Python 3.10 or newer.
Set it up once, on your laptop:

```bash
cd smac-handshake-test
python3 -m venv .venv-handshake
source .venv-handshake/bin/activate   # Windows: .venv-handshake\Scripts\activate
pip install -r requirements.txt
```

Then run it against your public address with your token. On macOS or Linux
this reads the token over ssh, so it never appears on screen (it asks for your
UQ password once):

```bash
MCP_TOKEN=$(ssh <uq-username>@reit7820-xxxxxxxx.zones.eait.uq.edu.au cat /opt/mcp-agent/TOKEN.txt) \
  python handshake.py https://reit7820-xxxxxxxx.uqcloud.net/mcp --json ../handshake_report.json
```

On Windows, read the token on the zone with `cat /opt/mcp-agent/TOKEN.txt`,
then set it before running `python handshake.py ...`: `set MCP_TOKEN=<token>` in
Command Prompt, or `$env:MCP_TOKEN="<token>"` in PowerShell.

The run ends with `HANDSHAKE PASSED` and writes `handshake_report.json` at the
top of the repo.
Commit that report as your proof. Never commit the token itself.

Last, give your token to your tutor through the setup form (choose
**Access token**), so the Orchestrator can call you.

## 8. Change something

1. Edit and test on your laptop with Docker, as in the README.
2. Commit and push to the default branch.
3. On the zone: `sudo mcp-deploy`.
4. Run the handshake test again.

Do the whole loop once before the Showcase, so you know it works.

## Day to day

| Task | Command (on the zone) |
|---|---|
| Deploy your latest commit | `sudo mcp-deploy` |
| Is it running? | `systemctl status mcp-agent` |
| Read the logs | `sudo journalctl -u mcp-agent -n 50` (add `-f` to follow) |
| Set or remove a secret | `sudo mcp-env set KEY`, `sudo mcp-env unset KEY` |
| New access token | `sudo mcp-token rotate`, then tell your tutor the new value |

## Troubleshooting

| What you see | What to do |
|---|---|
| `git clone failed` with `Repository not found` | The deploy key is not on this repo. Run the `ssh -T` check in step 5: it names the repo the key is on. Use the `git@github.com:` address |
| Deploy says `ANTHROPIC_API_KEY` is not set or was rejected | `sudo mcp-env set ANTHROPIC_API_KEY` with a working key, then deploy again. If sudo asks for your password first, paste the key only at the second prompt |
| `no repository has been deployed yet` | No deploy has succeeded yet. Run `sudo mcp-deploy git@github.com:<owner>/<repo>.git` with the full address |
| Deploy rolls back and mentions `0.0.0.0` | Your agent still binds `0.0.0.0`. Fix the `mcp.run(` line (step 1), push, deploy |
| Deploy says a file such as `server.py` is missing | `mcp-agent.toml` is missing from the default branch |
| Deploy says files were edited on the zone | `sudo git -C /opt/mcp-agent checkout -- .` then `sudo mcp-deploy`. Change code on GitHub only |
| `systemctl status` is not `active (running)` | Read `sudo journalctl -u mcp-agent -n 50`. Usually a missing key, or a crash in your own code |
| 401 in a browser | Normal without a token |
| 502 in a browser | The agent is not running, or you used the ssh address. The web address ends in `uqcloud.net/mcp` |
| Handshake says the token was rejected | Copy the whole token from `/opt/mcp-agent/TOKEN.txt` again |
| Handshake says it needs the 1.x MCP SDK, or `pip` cannot find `mcp>=1.27` | Recreate the handshake venv with Python 3.10 or newer |
| On Windows, curl reports `CRYPT_E_NO_REVOCATION_CHECK` | Add `--ssl-no-revoke` |

More detail: *REIT7820: Deploying Your MCP Server to UQCloud* (Kai Li Lim).
Stuck? Bring it to the Wednesday or Thursday workshop, or post on Ed with the
error message. Never post your API key or token.
