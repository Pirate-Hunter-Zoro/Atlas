# The block on api.deepseek.com

**One hostname is filtered. `api.deepseek.com` is reset during the TLS handshake from every c3
compute node, while DeepSeek's marketing site on the same IP answers normally.** The ask at the
bottom is a firewall exception for one name on one port. No client setting reaches a device that
resets the connection this early.

## What is blocked, and at which layer

DNS resolves and TCP connects. The reset lands on the ClientHello, the first packet carrying the
hostname in the clear.

```
$ getent ahosts api.deepseek.com
3.173.21.63     STREAM d3bbv8sr76az5s.cloudfront.net

$ curl -v https://api.deepseek.com/
*   Trying 3.173.21.63:443...
* Connected to api.deepseek.com (3.173.21.63) port 443 (#0)
* TLSv1.3 (OUT), TLS handshake, Client hello (1):
curl: (35) OpenSSL SSL_connect: Connection reset by peer

$ openssl s_client -connect api.deepseek.com:443 -servername api.deepseek.com
write:errno=104
SSL handshake has read 0 bytes and written 330 bytes
```

Zero bytes read: no ServerHello, no certificate, no alert. A bare RST, five times out of five,
14 ms after a 7 ms TCP connect.

**The filter keys on the name, not the address.** Four DeepSeek hostnames resolve to the identical
IP 3.173.21.63 and get two different answers:

| hostname | port 443 | port 80 |
|---|---|---|
| `www.deepseek.com` | HTTP 200, cert `CN=*.deepseek.com` | HTTP 301 |
| `deepseek.com` | HTTP 200 | — |
| `api.deepseek.com` | RST on ClientHello | RST after the `Host:` header |
| `chat.deepseek.com` | RST on ClientHello | — |
| `platform.deepseek.com` | RST on ClientHello | — |

**The tutor daemon gets the same answer as a shell.** A turn taken by the board's own headless
process spends about three minutes retrying and ends `API Error: Connection dropped (ECONNRESET)`
having billed nothing; `courses/Probability/live/agent.log` carries one. Nothing about the filter
is specific to an interactive session, so nothing about running the turn from somewhere else on
the node gets around it.

**The port 80 row places the device.** A cleartext `GET /` with `Host: api.deepseek.com` draws
`Recv failure: Connection reset by peer`. An origin refusing a request returns an HTTP status.
Only an on-path device reading the SNI and the `Host` header gives a silent RST for one name and a
clean 200 for its sibling.

ICMP is filtered network-wide, so `tracepath` returns ten hops of `no reply` and cannot place it.
Measured on compute305 and reproduced identically on compute300 and compute301: site policy, not
one sick node.

## Controls

All complete TLS from the same shell, in the same minute:

```
api.anthropic.com      http=404  tls=0.029s
github.com             http=200  tls=0.096s
huggingface.co         http=200  tls=0.078s
api.openai.com         http=421  tls=0.064s
```

**The policy is not about China.** `api.moonshot.cn` (200), `open.bigmodel.cn` (200),
`dashscope.aliyuncs.com` (404), `api.minimax.chat` (301) and `www.baidu.com` (200) all answer.

**There is no sanctioned route around it.** `/etc/environment` is empty, no `proxy` appears in
`/etc/profile.d`, no `~/.curlrc` or `~/.netrc` exists, and no proxy variable is set. Tailscale's
exit-node rotation in `board/tutorboard/net/egress.py` repairs a node with *no* egress; it does
nothing about a per-hostname filter.

## The client is not the problem

**The `claude` binary dispatches to whatever `ANTHROPIC_BASE_URL` names, carrying whatever
`ANTHROPIC_MODEL` says.** Pointed at a local listener with `ANTHROPIC_MODEL=deepseek-flash`, 2.1.281
POSTs `/v1/messages?beta=true` with `"model":"deepseek-flash"` in the body and reports the
listener's status back as the turn's error. The `[claude-code:unrecognized_model]` line it prints
on stderr for any id outside Anthropic's own lineup is cosmetic: its one effect is that fast mode
is off. Read as a refusal it sends the reader looking for a client setting that does not exist,
and `duration_api_ms: 0` alongside it is what a request that errored reports rather than evidence
that none was made.

## Why this machine needs it

These nodes run a tutoring board that teaches the owner's coursework. The assistant driving a
lesson is a documented commercial endpoint on a paid account, and the key is already in place. The
traffic is one HTTPS POST per turn carrying course mathematics and the owner's handwriting.

**No PHI goes near this route, and that is enforced in code.** `ai-config/policy/phi.py` fences the
`phi/` directory and every session-derived artifact by name, in front of the tool call, for every
assistant — this one included, since it runs through the same binary and inherits the same hook.
`ai-config/policy/egress.py` is the other half, refusing the network verbs to anything that read
inside the fence. The therapy audio in `research/PSYCH-ASR/phi/` is served only by colibrì, the
local model held warm behind a loopback gateway, and that does not change.

## The ask

**Allow outbound TCP 443 from compute300–compute306 to `api.deepseek.com`.**

By hostname rather than address: it is a CloudFront CNAME (`d3bbv8sr76az5s.cloudfront.net`) whose
IP rotates, and the sibling names on that same IP are already permitted.

## Re-test once it is open

```bash
curl -sS -o /dev/null -w '%{http_code}\n' https://api.deepseek.com/anthropic/v1/messages
```

Any HTTP status, 401 and 405 included, means the path is open. That URL is the endpoint the
`deepseek` recipe in `board/bin/tutor` already probes, so a number there is the number the tutor
sees.

Check the model name in the same sitting. `ANTHROPIC_MODEL` in that recipe is the one field that
goes stale, and `GET https://api.deepseek.com/models` dies in the same handshake as a turn, so it
cannot be checked until the name is open.
