# JobHai Jaipur Job Scraper

A small Python project that collects the latest full-time JobHai listings for
Jaipur, opens each public job page, and saves the results to CSV.

## Files

- `scraper.py` loads public JobHai pages and writes the CSV.
- `jobhai_session.py` owns OTP login, saved-session access, and authenticated
  recruiter-contact requests. Ship its obfuscated build, not its source.
- `parser.py` converts listing and detail HTML into structured job records.
- `webapp.py` displays every CSV field in a Flask webapp.
- `jobhai_jaipur_jobs.csv` is the generated sample output.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 -m playwright install firefox chromium webkit
```

On Windows, use `python` instead of `python3` if needed. Activate the virtual
environment with `.venv\Scripts\activate`.

## Run the scraper

```bash
python3 scraper.py --output jobhai_jaipur_jobs.csv
```

The default run collects up to 10 full-time Jaipur jobs and opens each detail
page for the full job description. It does not reuse old CSV data when a live
scrape fails.

Useful options:

```bash
python3 scraper.py --limit 5 --output data.csv
python3 scraper.py --browser chromium --output data.csv
python3 scraper.py --print-json
```

The CSV columns are:

```text
job_title, company, location, salary, job_type, experience, posted,
job_description, contact_person, recruiter_phone, recruiter_email, job_url
```

## Contact data and privacy

The normal scrape uses only public pages. To collect recruiter contact through
the same authorized API flow as JobHai's **Call HR** button, create a session
once:

```bash
python3 -m jobhai_session setup
python3 -m jobhai_session status
```

Enter the phone number and OTP for an account you are authorized to use. The
setup command obtains the session values and stores them through the operating
system credential store (macOS Keychain, Windows Credential Locker, or a
configured Linux Secret Service). Do not paste credentials into a Python file,
the README, a `.env` file, or Git. There is no token file to place manually.

Then run:

```bash
python3 scraper.py --include-recruiter-contact --output data.csv
```

If the saved session expires, repeat the setup command. To remove it from the
credential store, run:

```bash
python3 -m jobhai_session clear
```

The non-obfuscated scraper only imports `SessionError` and
`open_contact_client`. Credential names, headers, cookies, device identity,
login endpoints, and authenticated contact requests stay inside
`jobhai_session.py`. The actual secret values remain in the OS credential store
and are never embedded in either source or obfuscated code. See the
[keyring backend documentation](https://keyring.readthedocs.io/en/latest/) for
platform details.

An older `jobhai_auth.json` file is not read by this version. After the new
setup command reports success, remove that legacy file so a plaintext session
is not left on disk.

The reverse-engineered frontend sequence is:

```text
OTP login -> POST api.jobhai.com/jobs/v3/call
          -> POST www.jobhai.com/v1/utils/getInfo
```

The scraper follows `call_allowed` and decrypts a contact only when JobHai's
normal logged-in flow permits it. Calling this API may register application or
call activity, so use an account authorized for the assignment.

The observed Call HR response provides a phone contact but no recruiter email
field. Email is therefore extracted from public job-page text when present.
Unavailable contact fields are stored as `Not available`; the scraper does not
fabricate them.

JobHai normally places recruiter phone numbers behind its logged-in **Call HR**
workflow. An endpoint being callable from browser code does not make private
contact data a supported public API. This project therefore does not bypass that
access control or publish account credentials.

## Build the protected auth module

Use a descriptive module name so imports remain auditable. A random or
misleading filename does not add meaningful protection. PyArmor creates an
obfuscated replacement plus a required runtime package; distribute the whole
generated folder and do not distribute the source `jobhai_session.py`.

From the project root and with the virtual environment active:

```bash
python3 -m pip install pyarmor
rm -rf protected
pyarmor gen -O protected jobhai_session.py
cp scraper.py parser.py webapp.py requirements.txt protected/
```

The protected layout will contain the plain entry points, the obfuscated
`jobhai_session.py`, and a generated `pyarmor_runtime_*` directory. Test the
build from that directory so Python imports the protected copy:

```bash
cd protected
python3 -m jobhai_session status
python3 scraper.py --include-recruiter-contact --output data.csv
```

For first-time setup on a target computer, run
`python3 -m jobhai_session setup` from inside `protected`. The credential is
placed in that computer's OS credential store, not in the distribution folder.
Build on the same OS, CPU architecture, and Python minor version used to run the
protected output because the generated PyArmor runtime is platform and Python
version dependent. Refer to the
[official PyArmor command reference](https://pyarmor.readthedocs.io/en/latest/reference/man.html)
for additional build options.

`protected/` and `dist/` are ignored by Git. Obfuscation raises the cost of
reading implementation details; it is not a substitute for credential storage,
authorization checks, or secret rotation.

## Run the webapp

```bash
python3 webapp.py
```

Open `http://127.0.0.1:5000` and click **Load Jobs**. The app reads
`jobhai_jaipur_jobs.csv` and displays all columns.

## Troubleshooting

If Playwright reports `NS_ERROR_NET_RESET`, install every browser backend and
retry with a different one:

```bash
python3 -m playwright install firefox chromium webkit
python3 scraper.py --browser chromium --output data.csv
```

If all browsers fail on one connection, retry from a different network. JobHai
may reset automated browser requests at the network edge.
