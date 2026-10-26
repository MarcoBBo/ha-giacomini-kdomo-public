#!/usr/bin/env python3
"""Fill real repository metadata locally; never creates or publishes anything."""

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repository", default="ha-giacomini-kdomo")
    parser.add_argument("--maintainer", required=True, help="Individual GitHub username, without @")
    args = parser.parse_args()
    username_pattern = r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?"
    for value in (args.owner, args.maintainer):
        if not re.fullmatch(username_pattern, value) or value.upper() in ("OWNER", "TUO-USERNAME"):
            parser.error("Provide a real GitHub owner and individual maintainer")
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", args.repository) or args.repository in (".", ".."):
        parser.error("Invalid repository name")
    path = ROOT / "custom_components/kdomo/manifest.json"
    manifest = json.loads(path.read_text())
    url = f"https://github.com/{args.owner}/{args.repository}"
    manifest["documentation"] = url + "/blob/main/README.md"
    manifest["issue_tracker"] = url + "/issues"
    manifest["codeowners"] = ["@" + args.maintainer]
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    openapi_path = ROOT / "docs/openapi.json"
    openapi = json.loads(openapi_path.read_text())
    openapi["externalDocs"]["url"] = url + "/blob/main/docs/PROTOCOLLO_KDOMO.md"
    openapi_path.write_text(json.dumps(openapi, indent=2) + "\n")
    (ROOT / ".github/CODEOWNERS").write_text(f"* @{args.maintainer}\n")
    print(f"Local metadata configured for {url}. No repository created or published.")


if __name__ == "__main__":
    main()
