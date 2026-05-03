---
description: Create or renew OpenVPN server and user certificates via the OPNsense API. Writes certs, keys, and .ovpn configs to vpn-configs/.
argument-hint: [server | user <username> [<username2> ...] | renew-all]
allowed-tools: Read, Write, Edit, Bash
---

Create or renew OpenVPN certificates for the Know My Network project.

The argument is: $ARGUMENTS

The project base is: /Users/ppowell/Documents/vibe-coder-framework/project-001
The output directory is: /Users/ppowell/Documents/vibe-coder-framework/project-001/vpn-configs
The secrets file is: /Users/ppowell/Documents/vibe-coder-framework/project-001/secrets.encrypted.yaml

---

## Step 1 — Parse the arguments

Determine what to create based on `$ARGUMENTS`:

- `server` → create/renew the `vpn-server` certificate only
- `user <name> [<name2> ...]` → create/renew client certs for the named users
- `renew-all` → create/renew `vpn-server` + all users currently in `secrets.encrypted.yaml` under `openvpn_users`
- No arguments → ask: "Create `server`, `user <name>`, or `renew-all`?"

---

## Step 2 — Load OPNsense credentials from SOPS

Run:

```bash
SOPS_AGE_KEY_FILE=~/.config/sops/age/keys.txt \
  /opt/homebrew/bin/sops -d /Users/ppowell/Documents/vibe-coder-framework/project-001/secrets.encrypted.yaml
```

Extract `pfsense.api_key` and `pfsense.api_secret`. Use the venv Python (`/Users/ppowell/Documents/vibe-coder-framework/project-001/.venv/bin/python3`) to parse the YAML output.

These credentials are held in memory only — never written to disk, never logged.

OPNsense base URL: `https://gateway.powellcompanies.com`
Auth: HTTP Basic — api_key as username, api_secret as password.
All requests use `-sk` (skip TLS verification, self-signed cert).

---

## Step 3 — Find the OpenVPN-CA UUID

```bash
curl -sk -u "$KEY:$SECRET" \
  "https://gateway.powellcompanies.com/api/trust/ca/search"
```

Find the entry where `descr` contains `OpenVPN-CA`. Extract its `refid` field (the value used as `caref` in cert creation). If not found, stop and tell the user.

---

## Step 4 — Create the certificate(s)

For each cert to create, POST to `/api/trust/cert/add`:

**Server cert** (`vpn-server`):
```json
{
  "cert": {
    "action": "internal",
    "caref": "<OpenVPN-CA refid>",
    "type": "server",
    "dn_commonname": "vpn-server",
    "dn_country": "US",
    "dn_state": "Texas",
    "dn_city": "San Antonio",
    "dn_organization": "",
    "dn_email": "",
    "lifetime": 397,
    "digest_alg": "sha256",
    "keytype": "RSA",
    "keylen": 2048
  }
}
```

**Client cert** (one per user, e.g. `miketerry`):
```json
{
  "cert": {
    "action": "internal",
    "caref": "<OpenVPN-CA refid>",
    "type": "client",
    "dn_commonname": "<username>",
    "dn_country": "US",
    "dn_state": "Texas",
    "dn_city": "San Antonio",
    "dn_organization": "",
    "dn_email": "",
    "lifetime": 397,
    "digest_alg": "sha256",
    "keytype": "RSA",
    "keylen": 2048
  }
}
```

> IMPORTANT: Always use `"action": "internal"`. Never use `"action": "reissue"` — it ignores `lifetime` and produces certs with a year-2053 expiry (OPNsense bug).

The response will contain `{"result": "saved", "uuid": "<new-uuid>"}`. Save the UUID.

---

## Step 5 — Retrieve the cert and key

GET `/api/trust/cert/get/<uuid>` for each new cert.

The response fields `cert.crt` and `cert.prv` are base64-encoded PEM blocks. Decode them:

```python
import base64
cert_pem = base64.b64decode(resp["cert"]["crt"]).decode()
key_pem  = base64.b64decode(resp["cert"]["prv"]).decode()
```

Also retrieve the OpenVPN-CA public cert:
GET `/api/trust/ca/get/<ca-refid>` → decode `ca.crt` the same way.

---

## Step 6 — Write output files

Ensure `vpn-configs/` exists. Write the following files (overwrite if they exist):

**For the server cert:**
- `vpn-configs/vpn-server.crt` — server certificate PEM
- `vpn-configs/vpn-server.key` — server private key PEM

**For each client user `<username>`:**
- `vpn-configs/<username>-client.crt` — client certificate PEM
- `vpn-configs/<username>-client.key` — client private key PEM
- `vpn-configs/<username>-pgw-vpn.ovpn` — client config (see template below)

**Always (re)write:**
- `vpn-configs/OpenVPN-CA.pem` — CA certificate PEM

Set permissions `chmod 600` on all `.key` files.

### .ovpn template

```
client
dev tun
proto udp
remote pgw.powellcompanies.com 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth-user-pass
verb 3

<ca>
<OpenVPN-CA PEM goes here>
</ca>
```

The client cert and key are NOT embedded in the .ovpn — they are separate files loaded into the Synology certificate store.

---

## Step 7 — Update the OpenVPN server cert reference (server cert only)

If a new `vpn-server` cert was created, update the OpenVPN instance to use it:

1. GET `/api/openvpn/instances/get/a3f19734-4495-4554-a39c-496d535e5d05` to retrieve current config
2. Find the UUID of the new `vpn-server` cert: GET `/api/trust/cert/search`, match by `descr` = `vpn-server`, take the most recent (highest index or most recent `valid_from`)
3. POST `/api/openvpn/instances/set/a3f19734-4495-4554-a39c-496d535e5d05` with the full instance config, updating only the `cert` field to the new cert's UUID
4. POST `/api/core/service/restart/openvpn` to apply
5. POST `/api/firewall/filter/apply` to reapply firewall rules

Confirm the service came back up by checking logs: GET `/api/core/system/activity` or checking Elasticsearch for `openvpn_server1` entries.

---

## Step 8 — Print a summary

Output a table:

```
Certificate          Type    CN            Valid From    Valid Until   UUID
vpn-server           server  vpn-server    2026-04-29    2027-05-31    <uuid>
miketerry-client     client  miketerry     2026-04-29    2027-05-31    <uuid>
bianchi-client       client  bianchi       2026-04-29    2027-05-31    <uuid>
```

Then list the files written to `vpn-configs/`.

Remind the user:
- For each Synology device: go to **Control Panel → Security → Certificate**, select the OpenVPN-CA entry, **Action → Edit**, and replace the cert+key with the new `<username>-client.crt` and `<username>-client.key` files.
- If the server cert was renewed, OpenVPN has been restarted automatically.
- Set a calendar reminder ~2 weeks before the expiry date to renew again.
