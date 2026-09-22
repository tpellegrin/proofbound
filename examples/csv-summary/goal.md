Add opt-in strict input validation to this CSV summary library and CLI, preserving permissive
behavior by default. `totals(stream, strict=True)` must reject a missing or duplicate required
header, a blank category, a missing or extra row field, and a non-integer amount with ValueError.
The required headers are exactly `category,amount` in either order; extra headers are invalid in
strict mode. A valid header with zero data rows is allowed. Integer syntax is an optional ASCII
sign followed by one or more ASCII digits; whitespace around amounts is allowed. Negative and
zero values remain valid. Error messages must identify the header or physical data-row line number.

`cli.py --strict FILE` must use the strict library mode, emit an actionable error on stderr, exit 2,
and emit no partial summary on invalid input. Its default invocation and the existing one-argument
library API must retain their behavior. Keep sorted CLI output for valid input. Do not add runtime
dependencies. Add meaningful tests covering interactions between parsing, aggregation and CLI errors.
