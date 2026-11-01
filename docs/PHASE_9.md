# Phase 9 — Reliable mobile synchronization

## Added
- Persistent mobile outbox entries have unique change IDs and a stable device ID.
- Android queues readings and payments locally first, then attempts synchronization when the app refreshes or the user checks the connection.
- The API exposes idempotent `POST /sync/readings` and `POST /sync/payments` endpoints. Each requires `X-Idempotency-Key`; the Android client also sends `X-Device-Id`.
- The server stores the request key, payload hash, entity type, processing state and result. Repeating the same key and payload returns the stored response instead of recording another transaction. Reusing a key with different data returns HTTP 409.
- `GET /sync/requests/{request_key}` exposes a request's state; `GET /sync/status` provides recent server-side synchronization diagnostics.
- `GET /sync/pull` continues to provide audit-log change notifications. The Android app persists its cursor and refreshes canonical household, meter, bill and billing-period lists after polling.
- Permanent validation errors are moved to a local `review_required` queue state. Transient errors remain pending and stop the current replay pass.

## How to use
1. Start the API and sign in on Android.
2. Record readings or payments. They are saved to the local outbox first.
3. When the device reconnects, tap the sync icon or refresh the dashboard. Pending submissions are replayed in order.
4. Review the Offline queue and Needs review counts in Settings. Correct rejected data and submit it again as a new entry after review.

## Important safety behavior
- The old acknowledgement-only `/sync/push` endpoint now returns HTTP 410. Clients must use the validated idempotent reading/payment endpoints.
- A request left in `processing` or marked `review_required` is not blindly replayed. Check its server request status and audit records before manually creating a replacement. This avoids duplicate financial entries when a connection is lost after the server commits but before the phone receives the response.
- The idempotency reservation and business transaction are persisted in separate database transactions because existing service functions own their commits. A process crash in that narrow interval can leave a request requiring administrator review. The system deliberately blocks automatic retry in that state. A future phase should move both writes into one database transaction.
- Pull synchronization currently refreshes the app's supported list caches; it is not a full field-level merge engine and does not synchronize every desktop configuration or administrative action to the mobile UI.
- Offline queue data is stored in the app's SQLite database. Device loss, app-data clearing, or uninstalling can remove unsynchronized entries. Back up the device and sync regularly.
- Flutter SDK/device build and end-to-end multi-device network tests must be run on a development machine with Flutter and Android tooling installed.

## API reference
- `POST /sync/readings` — reading submission with idempotency headers
- `POST /sync/payments` — payment submission with idempotency headers
- `GET /sync/requests/{request_key}` — inspect one request
- `GET /sync/status` — recent request summary (authenticated)
- `GET /sync/pull?after_id=0&limit=500` — audit change feed
