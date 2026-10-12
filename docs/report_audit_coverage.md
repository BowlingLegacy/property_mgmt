# BowlingLegacy report audit coverage

Audit branch: `review/property-security-fixes`
Pinned base: `d206a272c344a8be14cb9c47c57b6018f98f54ef`
Audit date: 2026-10-12
Data boundary: synthetic test databases only; no production reads, snapshot rewrites, or deployment.

## Accounting contracts used

- Cash reports exclude service/labor credits and show those credits as non-cash memo activity.
- Payment allocation is by service month, with cent remainders assigned to the last covered month.
- Payment Summary is a cash-received view, filters by `received_at` (falling back to `created_at` only for legacy rows), and includes former residents.
- Property ledger attribution is row-level. New rows carry `FinancialEntry.property`; legacy name fallback is allowed only for a unique property name and property-ledger rows. Company rows are excluded from property reports.
- Summary/receipt precedence is resolved independently per property and month before portfolio aggregation.
- Unpaid deposits remain receivable for active and former residents until a separately modeled payment or waiver exists. Applied deposits reduce held liability without being represented as cash.
- T-12 is the selected calendar year (January–December), not rolling twelve months.
- Vendor expense totals include approved receipts only. Pending and ignored/duplicate receipt amounts remain visible as separately labeled, excluded totals.
- Valuation estimates require all twelve `AccountingPeriod` records for the property/year to be explicitly closed. A closed month without activity is a confirmed zero; an open or absent month is missing, and the valuation is withheld rather than annualized.

## Custom reports

| Output | Status | Checks / repairs |
|---|---|---|
| Resident Phone List | Checked | Scoped active resident population; shared property access rules. |
| Resident Roster | Checked | Scheduled rent, stored balance, and unpaid deposit semantics retained. |
| Payment Summary | Fixed | Received-date filtering/label, former-resident inclusion, method/type/status retained. |
| Delinquency | Fixed | Prior balance plus current shortfall; active/former unpaid deposits included. |
| Deposit Liability | Fixed | Required, paid, applied, still-held and unpaid amounts separated; former residents retained. |
| Property Performance | Checked / labeled | Uses the calendar-year T-12 engine; occupancy month and current open balances remain separately labeled concepts. A single shared period is not inferred. |
| Valuation Estimate | Fixed | Uses actual calendar-year NOI only after all 12 property accounting months are explicitly closed. Missing/open months produce a clear incomplete status and no estimate; closed zero-activity months are confirmed zeroes. |
| Income Statement / P&L | Fixed | Per-property/month precedence, service-month allocation, cash/noncash cutoff, partial-date filtering, golden NOI/debt/capital arithmetic. |
| Expense by Category | Fixed via shared scope | Stable row attribution and ledger-scope filtering; legacy month-only rows are retained when the requested period includes their month. |
| Vendor Expense | Fixed | Approved expenses are the only counted total. Pending and ignored/duplicate amounts are separately labeled and excluded. Each receipt header or split lineage is counted once, never both. |
| Occupancy / Vacancy | Checked / blocked historically | Current effective room inventory and tenancy dates used. Historical room-rate/inventory reconstruction needs effective-dated room history. |
| Capital Improvement Log | Fixed via shared scope | Stable property attribution and date handling. |
| Utility Cost Trend | Checked / labeled gap | This is a cost trend; no utility usage quantity model exists, so it must not be described as metered usage. |
| Insurance / Compliance | Checked / labeled gap | Provider/link/insurance-cost inventory only; no verified coverage/compliance model exists. |
| Supportive Housing / Lender Package | Fixed | Removed Painted Lady narrative and hard-coded acquisition/deposit/grant figures; output is explicitly an incomplete draft requiring property-specific verification. |
| Financial Entries | Fixed | Stable attribution, company exclusion, legacy unique-name fallback, exact-date and legacy-month handling. |

All custom-report invalid choices, inaccessible properties, invalid dates, and reversed ranges now render form errors and do not render an empty generated report. Print headers retain property scope, period/basis and generation date. Generic second-column right alignment was removed.

## Standalone and supporting surfaces

| Output | Status | Checks / repairs |
|---|---|---|
| Payment Log HTML / CSV | Fixed | Shared active + real-former completed-payment population; `month=all`; CSV adds IDs, property, unit, method, reference and balances; spreadsheet-formula text neutralization. |
| Rent Roll HTML / CSV | Fixed | Future tenants cannot overwrite current occupants; overlapping tenancies remain distinct; snapshot charge freezes actual obligation rather than overpayment; property/resident exported; scheduled rate, actual charge, prior balance and total due distinguished. |
| T-12 HTML / CSV | Fixed | Per-property precedence, allocation parity, capital and net cash flow visibility, receipt income, projection basis limited to elapsed months. |
| Property Financials | Fixed | ID-based scoped access; template KPI contract populated from current rent receipts and shared T-12 engine. |
| Move-out Statement | Fixed with allocation contract | Only payments whose service month matches included charge months settle statement charges; deposit credit is capped after prior ledger deposit application; common Stripe reference fallback. |
| Payment Receipt | Fixed | Reference falls back from manual reference to Stripe intent/session. |
| Tenant balance/history | Fixed | Adjustment cents retained; future service-month history preserved by earlier candidate changes. |
| Landlord collection/attention | Checked | Additive carried balance and collectible deposit rules align with delinquency. |
| Owner dashboard | Fixed | YTD uses elapsed months from the shared T-12 engine; service credits excluded from cash metrics; portal fallback retained. |
| Superadmin summary | Checked | Uses scoped shared collections; no new arithmetic engine added. |
| Accounting receipts / bank review | Fixed via lineage | Approved entries receive stable row property attribution. Bank/company rows no longer inherit upload property in reports. |
| Former/current resident reconciliation | Checked | Former payment and deposit populations retained where financially relevant; upcoming tenants do not replace current rent-roll rows. |

## Security and concurrency verification

- Stripe webhook locks only the intended `Payment` row and `HousingApplication` row with `select_for_update(of=("self",))`; nullable `property` joins are not locked.
- PostgreSQL 17 synthetic tests cover duplicate delivery of one payment and simultaneous distinct payments against one resident balance.
- SQLite continues to skip the locking contract by design; PostgreSQL evidence is required for concurrency claims.

## Remaining explicit decisions / model gaps

1. Deposit waiver and refund need first-class ledger event types. Current fields can prove required, paid, applied, and still held, but cannot infer a waiver/refund safely.
2. Historical occupancy, room rate, transfer and inventory accuracy needs effective-dated room/lease history. Existing snapshots are not rewritten.
3. Insurance compliance and utility usage require dedicated verified data models; present reports cover cost/source inventory only.
4. The named-person rent override predates this audit. It should be migrated to a lease/resident/effective-date record after the underlying agreement is verified; this audit does not guess or remove that obligation.
5. Import parsing still needs a product decision for invalid monetary/date cells and same-valued legitimate transactions. Unreadable values should become review errors rather than inferred zero, but changing import acceptance policy without an exception workflow is unsafe.

## Verification limits

- Browser checks used synthetic records only at 390x844, 768x1024, and 1440x900. Custom Reports, Rent Roll, T-12, and Move-out Statement had no page-level horizontal overflow after repairing the T-12 mobile table; long names, a long processor ID, cents, and a seven-digit rent fixture were included.
- Print CSS was inspected for landscape sizing, hidden controls/navigation, wrapping, fixed table layout, repeating headers, and page-break rules. The connected Edge extension could invoke but not expose the native print-preview pane, so pixel-level print-preview confirmation remains outstanding.
- Historical rent-roll browser checks were avoided because GET/export can create snapshots.
- No production data, external lender facts, deployment, or push is part of this pass.
- No historical production snapshot is rewritten by these migrations.
