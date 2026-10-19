"""Small scheduled client; database credentials stay on the web service."""

import argparse, json, os, time
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--midnight-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.midnight_only and datetime.now(ZoneInfo("America/Los_Angeles")).hour != 0:
        print("Outside Pacific midnight hour; no assessment required.")
        return
    token = os.environ["LATE_FEE_JOB_TOKEN"]
    url = os.environ.get(
        "LATE_FEE_JOB_URL", "https://bowlinglegacy.com/internal/jobs/late-fees/"
    )
    data = json.dumps({"dry_run": args.dry_run}).encode()
    for attempt in range(3):
        try:
            req = Request(
                url,
                data=data,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urlopen(req, timeout=60) as r:
                result = json.load(r)
            print(json.dumps(result))
            return
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt == 2:
                raise SystemExit(
                    f"Late-fee job failed: {type(exc).__name__}; inspect service logs."
                ) from None
            time.sleep(10)


if __name__ == "__main__":
    main()
