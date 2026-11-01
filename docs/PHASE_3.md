# Phase 3 — Billing controls and account integrity

## Implemented in this milestone

1. Bill generation requires a saved custom billing period. The period must be open, and the selected effective date must be inside its start/end range. The period’s saved due date is used for the bill.
2. Arrears are derived from the outstanding amount on the household’s latest previous bill. This avoids summing several historical bills whose totals already include earlier arrears.
3. Payments validate the outstanding amount, update Paid/Partially paid status in the same transaction, and create an audit record.
4. The desktop refresh recalculates overdue status using the due date.
5. Dashboard outstanding uses the latest bill for each household so carried-forward arrears are not counted repeatedly. Billed totals show water charges across generated periods.
6. Meter replacement captures old meter final reading, new meter initial reading, replacement date, reason and authorizing administrator. The old meter is deactivated; the new meter inherits the household and meter type. Historical readings remain attached to the old meter.
7. Startup adds missing `due_date` and `status` columns to older bill tables.

## Important operating notes

- Create the custom billing period before recording readings and generating bills for it.
- Use the same period name consistently for the billing period and meter readings.
- A payment is currently recorded against one selected bill. The full household-level payment allocation and receipt ledger are future work.
- Meter replacement stores the final and initial values in the replacement history. The operator must enter the new meter's first billing-period reading using the recorded initial value as its previous reading.
- The replacement workflow does not yet include a separate supervisor approval role or password re-authentication.

## Not production-ready yet

Role-based authentication, payment reversals, household statements, full ledger allocations, complete audit coverage, concurrency testing, end-to-end tests, API, Android client, sync conflict resolution, installer packaging and security review remain outstanding. Back up the database before testing with real records.
