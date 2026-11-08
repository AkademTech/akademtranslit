# Security policy

## Supported versions

Fixes are released for the latest minor version only (currently 0.2.x). Older
versions are not patched; upgrade to the latest release.

## Reporting a vulnerability

Please report privately, not in a public issue:

- on GitHub, with **Report a vulnerability** on this repository's Security tab
  (private vulnerability reporting); or
- by email to contact@akademtech.org.

Include the version, the smallest input that shows the problem, and what you
expected to happen. We do not promise a response time.

## Scope

AkademTranslit is a pure-Python library with no dependencies. It opens no
network connections and stores no data: it takes a string and returns a
string. Reports in scope are about the library itself, for example an input
that makes a function crash or take unreasonable time, or output that breaks a
documented guarantee in a way that can be abused (such as a mixed-script
string that `script_class` reports as single-script). How an application uses
the output is out of scope.
