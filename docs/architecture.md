# Module boundaries

HTTP routes call application operations in `reads`, `field_parsers`,
`email_sync`, `template_assignment`, and `transaction_extraction`.
Each operation owns a `database_connection()` scope and preserves an already
open caller-owned connection. Write operations also own their atomic transactions.

`queries` contains persistence reads and requires an active connection.
`models` defines Peewee records, storage conversions, and save-time validation.
Neither layer depends on the HTTP API.

`parser_configuration` owns reusable parser types and validation rules.
`email_content` selects normalized HTML text with a plain-text fallback.
`template_syntax` defines parameter markers, while `template_mining` adapts
Drain3 results into application-owned values. `template_representation` extracts
parameters and resolves fields without database access.

`reads` loads templates and parser configurations in batches and prepares
representations. Its `read_models` results contain detached values, so
`api.serializers` can construct response schemas after the connection closes.
Serializers must not query, normalize content, or execute parsing.

Parser replacement validates before deleting existing rows and prepares its
preview inside the same transaction. Preview failure therefore rolls back
the replacement. Extraction loads each template's parser configuration once,
skips incomplete configurations, and commits transactions per template.

HTTP contracts and database schema are unchanged by these boundaries.
Core import direction and serialization/query behavior have regression tests.
