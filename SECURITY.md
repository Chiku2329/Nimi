# Security policy

## Reporting a vulnerability

Please do not publish exploit details in a public issue.

Use GitHub's private vulnerability reporting feature for this repository if it is enabled. If it is unavailable, contact the repository owner privately through GitHub before disclosing the issue publicly.

Include:
- A concise description of the affected component.
- The impact and conditions required to reproduce it.
- A minimal proof of concept that does not access other users' data or damage systems.
- A suggested mitigation, if known.

Do not include API keys, database URLs, guest cookies, private chat content, or other secrets in reports.

## Maintainer response checklist

1. Confirm the affected branch and deployed version.
2. Reproduce safely in an isolated staging environment.
3. Patch the staging branch and add a regression test.
4. Review dependency advisories and rotate any potentially exposed credentials.
5. Deploy only after tests pass and the owner explicitly approves the release.

## Supported security posture

Nimi is an anonymous public application. Anonymous access does not imply shared sessions: each visitor must have a separate identity and private chat history.

The application must not provide public shell access, arbitrary code execution, unrestricted filesystem access, or agent self-modification. Secrets must remain in the hosting provider's environment settings and must never be committed to Git.
