import argparse
import json
from sending_records import InfraiClient, verify_domain


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify an email sending domain")
    parser.add_argument("domain")
    parser.add_argument("--idempotency-key")
    args = parser.parse_args()
    result = verify_domain(InfraiClient(), args.domain, args.idempotency_key)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
