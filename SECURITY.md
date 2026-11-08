# Security policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Report vulnerabilities privately through [GitHub's private vulnerability reporting](https://github.com/klconsultancy/aiophoenixcontactcharx/security/advisories/new), not in a public issue.

Include what an attacker can do, the steps to reproduce it, and the affected version or commit. You will get an answer within a week. Once a fix is released, the advisory is published with credit to you unless you prefer otherwise.

The library talks Modbus/TCP to a CHARX controller, which has no authentication of its own, and can change charging current and release charging. Issues that let the library write to registers the caller did not ask for, or that make it misreport a controller's state, are treated as the most severe.
