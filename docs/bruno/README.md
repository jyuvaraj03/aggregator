# Aggregator Bruno collection

This collection exercises the local Aggregator API. It does not need authentication.

1. Apply the database migrations and start the API from the repository root:

   ```bash
   uv run pwmigrate up
   uv run aggregator-api
   ```

2. Open `docs/bruno` as a collection in [Bruno](https://www.usebruno.com/).
3. Select the `Local` environment. Its `baseUrl` is `http://127.0.0.1:8000`.

The `Get ... by ID` requests use `1` as an example; change it to an ID returned
by the corresponding list request. `Sync Email` requires configured local Gmail
Application Default Credentials, as described in the repository README. Its request
documentation shows how the sync job links to template assignment and how template
assignment links to each parser-generation job. Use `Jobs / Check Job` for every ID.
