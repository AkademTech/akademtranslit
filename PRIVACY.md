# Privacy

AkademTranslit is a library. It runs inside the program that calls it; it is
not a service.

- It collects no data. Each function works only on the arguments it is given
  and returns a result; nothing is kept between calls.
- It opens no network connections and reads or writes no files. The package
  imports two standard-library modules, `re` and `unicodedata`, and
  `tests/test_privacy.py` fails if that changes.
- It has no telemetry, analytics or update checks.

Text passed to the library may contain personal data, such as names. The
application that passes it decides how that data is collected, stored and
shared, and is responsible for it under the laws that apply to that
application.

## Privacy questions

The Digital Public Goods Standard asks six privacy questions. For this
library:

- **Minimum data.** None is collected.
- **How users are told.** There is nothing to collect, so nothing to tell;
  this file states it.
- **Where personal data is processed.** Only inside the calling program, in
  memory, for the duration of one function call. No component of the library
  stores or sends it.
- **Deletion.** Nothing is kept, so there is nothing to delete.
- **Retention.** None. The library keeps no copy of any text.
- **Access.** The maintainers have no access to any user's data.

AkademTranslit is owned and maintained by AKADEMTECH MChJ. Questions:
contact@akademtech.org.
