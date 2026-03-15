# Oracle Database Setup — TriptokForge
## Complete Guide: Autonomous DB + Object Storage

---

## STEP 1 — Create Autonomous Database (Transaction Processing)

1. Go to **cloud.oracle.com** → login → hamburger menu
2. **Oracle Database** → **Autonomous Database**
3. Click **Create Autonomous Database**
4. Fill in:
   - Display name: `triptokforge-db1`
   - Database name: `TRIPTOKDB1`
   - Workload type: **Transaction Processing**
   - ✅ Always Free
   - Password: create a strong one and store it only in your protected Oracle server secret store
5. Click **Create Autonomous Database**
6. Wait ~2 minutes for it to provision (STATUS = AVAILABLE)

---

## STEP 2 — Download Wallet

1. Click your new database → **Database connection**
2. Click **Download wallet**
3. Set wallet password (can be same as DB password)
4. Download the ZIP

**On Oracle VM:**
```bash
mkdir -p ~/wallet
# Upload wallet ZIP to Oracle VM first, then:
cd ~/wallet
unzip /tmp/Wallet_TRIPTOKDB1.zip
ls ~/wallet
# Should see: cwallet.sso, ewallet.p12, tnsnames.ora, sqlnet.ora, etc.
```

---

## STEP 3 — Install Python Oracle Driver

```bash
pip install oracledb --break-system-packages
```

No Oracle Client libs needed — oracledb works in thin mode.

---

## STEP 4 — Find Your Connection String

```bash
cat ~/wallet/tnsnames.ora
```

Look for lines like:
```
triptokdb1_high = (description= ...)
triptokdb1_medium = (description= ...)
triptokdb1_low = (description= ...)
```

Use `triptokdb1_high` for your DSN.

---

## STEP 5 — Add Environment Variables via Protected Env File

Use a protected Oracle-only secret source. OCI Vault is the strongest long-term option; a root-only env file is the minimum acceptable local pattern.

```bash
sudo install -m 600 /dev/null /etc/islandforge.env
sudo nano /etc/islandforge.env
```

Add:
```ini
ORACLE_DSN=triptokdb1_high
ORACLE_USER=ADMIN
ORACLE_PASSWORD=YOUR_REAL_DB_PASSWORD_SET_ONLY_ON_SERVER
ORACLE_WALLET=/home/ubuntu/wallet
```

Then make sure the systemd unit contains:

```ini
EnvironmentFile=/etc/islandforge.env
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart islandforge
```

---

## STEP 6 — Initialize Schema

```bash
cd ~/ver-perlinforge/islandforge
python3 -c "from oracle_db import init_schema; init_schema()"
```

You should see:
```
[oracle_db] Schema ready.
```

---

## STEP 7 — Create OCI Object Storage Bucket

1. In Oracle Cloud Console → hamburger → **Storage** → **Buckets**
2. Click **Create Bucket**
   - Name: `triptokforge`
   - Visibility: **Public** (so audio URLs work without auth)
   - Storage tier: Standard
3. Click **Create**

---

## STEP 8 — Create API Key for OCI SDK

1. Click your user avatar (top right) → **User settings**
2. **API Keys** → **Add API Key**
3. Generate key pair (download both)
4. Copy the config preview shown — it looks like:

```ini
[DEFAULT]
user=ocid1.user.oc1..aaaa...
fingerprint=aa:bb:cc:dd:...
tenancy=ocid1.tenancy.oc1..aaaa...
region=us-ashburn-1
key_file=~/.oci/oci_api_key.pem
```

**On Oracle VM:**
```bash
mkdir -p ~/.oci
nano ~/.oci/config
# Paste the config above

nano ~/.oci/oci_api_key.pem
# Paste your private key

chmod 600 ~/.oci/oci_api_key.pem
chmod 600 ~/.oci/config
```

---

## STEP 9 — Find Your Tenancy Namespace

```bash
python3 -c "
import oci
config = oci.config.from_file()
client = oci.object_storage.ObjectStorageClient(config)
ns = client.get_namespace().data
print('Namespace:', ns)
"
```

---

## STEP 10 — Add OCI Environment Variables

```bash
sudo nano /etc/islandforge.env
```

Add:
```ini
OCI_NAMESPACE=your_namespace_from_step9
OCI_BUCKET=triptokforge
OCI_REGION=us-ashburn-1
OCI_CONFIG_FILE=/home/ubuntu/.oci/config
```

Reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart islandforge
```

---

## STEP 11 — Install OCI SDK

```bash
pip install oci --break-system-packages
```

---

## STEP 12 — Verify Everything

Hit the health endpoint:
```bash
curl http://127.0.0.1:5000/health
```

Should return:
```json
{
  "oracle_driver": true,
  "oracle_config": true,
  "oracle_online": true,
  "oci_sdk": true,
  "oci_config": true,
  "fallback_mode": false
}
```

---

## What Each Table Stores

| Table | Data |
|-------|------|
| `members` | Epic account ID, display name, avatar, skin choice |
| `audio_tracks` | Filename, weights, duration, uploader, OCI URL |
| `jukebox` | Community jukebox queue with votes |
| `announcements` | Admin announcements for community page |
| `island_saves` | Generation history, OCI URLs for preview/heightmap |

## What OCI Object Storage Holds

| Folder | Contents |
|--------|----------|
| `audio/` | All uploaded audio files |
| `previews/` | Island preview PNGs |
| `heightmaps/` | Island heightmap PNGs |
| `layouts/` | Island layout JSONs |

## Fallback Mode

If Oracle is not configured, the app falls back to:
- Audio files → `saved_audio/` on the VM disk
- Members → `data/members.json`
- Announcements → `data/announcements.json`

The app always works even without DB configured.

---

## Second Free Autonomous DB (Optional)

You can create a second Always Free DB for island/analytics data:
- Name: `triptokforge-db2`
- Workload type: **JSON Database** or **Data Warehouse**
- Same wallet process as above
- Use a separate env var: `ORACLE_DSN2=triptokdb2_high`
