# Event Ticketing & Seat Booking — Research, Requirements & Design

Oct 26, 2026 · @Vipul

## 1. Overview

The MVP is a single-organizer event ticketing platform: organizers publish events on a seat grid, customers hold and pay for seats through Razorpay test mode, and gate staff validate signed QR tickets at entry. Its core engineering goal is that no seat can ever be sold twice, even when many users pick it at the same moment.

**Problem statement (Hackathon topic #34).** Create a platform where organizers publish events with seating layouts, customers book seats with payment, and entry is validated at the venue using a QR ticket.

**Constraints.** 5 working days, one developer, assisted by Claude Code. Stack: Next.js (React) frontend, FastAPI (Python) backend, PostgreSQL, Docker, deployed to a public URL.

**What this document covers.** Market research on Indian and global ticketing platforms, the business process, user roles and permissions, functional and non-functional requirements, business rules, exception handling, scope and exclusions, high-level design, low-level design, API contracts, integrations, testing strategy and the 5-day delivery plan.

| Mandatory hackathon expectation | Where it is addressed |
| --- | --- |
| Research existing applications and processes | Sections 2, 3 |
| Roles, permissions, business rules, exceptions | Sections 4, 6, 7 |
| Requirements document and technical design | Sections 5, 8, 10, 11, 12 |
| React frontend + Python backend | Section 10 |
| Persistence, authentication, RBAC | Sections 4, 10, 11 |
| At least one meaningful third-party integration | Section 13 (Razorpay test mode) |
| Automated tests, validations, errors | Sections 7, 14 |
| Docker + deployment | Section 10 |
| Assumptions, limitations, exclusions | Section 9 |
| AI review report | Section 15 (Day 5) |

## 2. Market research

Every major platform solves the same three problems our MVP targets: seat contention at checkout, payment-to-booking consistency, and fraud-resistant entry. Indian live-event ticketing is a two-player market: BookMyShow and District (Zomato/Eternal), with Ticketmaster as the global reference for high-demand sales.

### 2.1 Indian market context

- **BookMyShow** is the market leader; Reuters described Indian online ticketing for movies and events as dominated by the Reliance-backed platform ([DealStreetAsia](https://dealstreetasia.com/?p=409437)).
- **District** is Zomato's (now Eternal's) going-out app. In August 2024 Zomato agreed to buy Paytm's ticketing business, Insider (events) and TicketNew (movies), for about Rs 2,048 crore, and migrated those users into District ([The Week / PTI](https://www.theweek.in/wire-updates/business/2024/08/21/del88-biz-ld-paytm-zomato.html)).
- District reported more than Rs 970 crore revenue in FY26 (Apr 2025 to Mar 2026), about 4x its level at the time of the acquisition, and is still loss-making ([The Ken](https://the-ken.com/story/district-isnt-even-2-of-eternals-business-but-its-enough-to-rattle-bookmyshow/)).
- After the acquisition, District added a "Book Now, Sell Later" resale feature so users who cannot attend can resell tickets ([The Ticketing Business](https://www.theticketingbusiness.com/?p=92259)).

### 2.2 Feature comparison

| Capability | [BookMyShow](https://in.bookmyshow.com) | District (incl. Paytm Insider) | [Ticketmaster](https://www.ticketmaster.com) | Our MVP |
| --- | --- | --- | --- | --- |
| Event types | Movies, events, sports, plays | Movies, events, sports, dining | Concerts, sports, theatre | Seated events (one venue type) |
| Seat selection | Seat map per show | Seat map for seated events | Interactive venue map | Grid seat map, row-based categories |
| Temporary seat hold | Countdown timer on payment page | Countdown timer on payment page | Time-boxed cart | 8-minute hold, all-or-nothing |
| High-demand traffic | Queue for large drops | Queue for large drops | Smart Queue virtual waiting room | Excluded (documented) |
| Pricing add-ons | Convenience / internet handling fee + GST | Convenience fee | Service fees, dynamic pricing | Flat convenience fee (configurable) |
| Entry validation | M-ticket with dynamic QR; screenshots rejected | QR ticket in app | SafeTix barcode refreshing every 15 s | Signed QR, single-use check-in |
| Cancellation by user | Only where venue/cinema allows; live events usually non-cancellable | Event-specific | Event-specific | Not allowed (organizer cancellation only) |
| Ticket transfer / resale | Limited | "Book Now, Sell Later" resale | Transfer + verified resale | Excluded |

### 2.3 Findings that shape our design

1. **Seat holds happen before payment.** Interview-grade designs of BookMyShow-like systems hold seats for about 10 minutes and release them if payment does not complete ([TechInterview LLD](https://techinterview.org/lld-movie-ticket-booking/)). We use 8 minutes, inside Razorpay's own checkout timeout.
2. **Multi-seat holds must be all-or-nothing**, otherwise a user can believe they hold seats 5A and 5B but only hold 5A ([TechInterview LLD](https://www.techinterview.org/post/3233463752/lld-movie-ticket-booking-system/)).
3. **"Money debited, ticket not booked" is the most common complaint** in public reviews of Indian ticketing apps ([Voxya complaints](https://voxya.com/consumer-complaints/payment-debited-but-no-tickets-received/267527)). Our design treats late or orphaned payments as a first-class exception with automatic refund.
4. **Refund handling is a trust issue.** Users complain about refunds going to a platform wallet instead of the original payment method ([MalwareTips summary](https://tools.malwaretips.com/url-scan/bookmyshow.com)). We always refund to source via Razorpay.
5. **Convenience fees are regulated territory.** Indian regulators and courts have questioned online convenience fees ([Deccan Herald](https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Finternet-handling-fee-under-scrutiny-731842.html), [MediaNama](https://www.medianama.com/2013/09/223-bookmyshow-may-exit-maharashtra-if-convenience-fee-issue-isnt-resolved/)). We show the fee as a separate line item before payment and refund it when the organizer cancels.
6. **Static QR codes are copyable.** BookMyShow M-tickets for IPL show a dynamic QR and reject screenshots ([Mumbai Indians guide](https://mumbaiindians.com/news/ipl-2025-m-tickets-guide-mumbai-indians-cricket)); Ticketmaster SafeTix refreshes the barcode every 15 seconds ([Atlanta Hawks FAQ](https://www.nba.com/hawks/managetickets)). Our MVP uses a signed, single-use QR; rotating codes are future scope.
7. **Virtual queues protect the seat-lock service** during big drops ([Ticketmaster Smart Queue](https://business.ticketmaster.com/smart-queue/)). Out of scope for a 5-day MVP, documented as a production consideration.

## 3. Business process

The event lifecycle passes through three roles in a fixed order, and the seat hold is the step every other step depends on: no hold, no payment; no confirmed payment, no ticket.

&#91;embedded content: booking lifecycle · 3 roles, 10 steps\]

Organizers set up and publish; customers move from browsing to a held seat to payment to a QR ticket; gate staff validate each ticket once. If the 8-minute hold runs out before payment, the seats go back on sale and the customer picks again.

**How this matches the industry.** BookMyShow and District both hold seats before showing payment, deliver a QR ticket in the app, and scan it at the venue entrance (Section 2). The MVP keeps that same order and leaves out queues, resale and transfers.

## 4. User roles and permissions

The MVP has four roles, carried as a claim in the JWT and enforced on every FastAPI endpoint; the Next.js middleware only hides routes and is not a security boundary.

| Role | Who | Main goal |
| --- | --- | --- |
| Customer | Any registered user (self sign-up) | Find an event, book seats, pay, show the QR at the gate |
| Organizer | Event company staff, created by Admin | Create venues and events, publish them, track sales, cancel events |
| Gate Staff | Venue staff, created by an Organizer for their events | Scan QR tickets and admit attendees |
| Admin | Platform operator (seeded account) | Manage users and roles, view all bookings, payments and refunds |

### 4.1 Permission matrix

| Action | Customer | Organizer | Gate Staff | Admin |
| --- | --- | --- | --- | --- |
| Sign up / log in | Yes | Log in | Log in | Log in |
| Browse published events and seat map | Yes | Yes | No | Yes |
| Hold seats and pay | Yes | No | No | No |
| View own bookings and QR tickets | Yes | No | No | No |
| Create / edit venue layout | No | Own | No | All |
| Create / edit event (draft) | No | Own | No | All |
| Publish / cancel event | No | Own | No | All |
| View bookings and sales for an event | No | Own events | No | All |
| Assign gate staff to an event | No | Own events | No | All |
| Scan and check in tickets | No | Own events | Assigned events | No |
| Trigger refunds | No | Via event cancel | No | Yes (manual) |
| Manage users and roles | No | No | No | Yes |

"Own" means the record's `organizer_id` equals the caller's user id; the check runs in the service layer, not only in the route.

## 5. Functional requirements

The MVP commits to 24 requirements: 18 Must (the demo fails without them) and 6 Should (built on Day 4 if time allows). Anything not listed is out of scope (Section 9).

| ID | Module | Requirement | Priority |
| --- | --- | --- | --- |
| FR-01 | Auth | Customer signs up with name, email, phone and password; password stored as bcrypt hash | Must |
| FR-02 | Auth | All roles log in with email + password and receive a JWT access token (role in claims) | Must |
| FR-03 | Auth | Every API checks role and ownership; unauthorized calls return 401/403 | Must |
| FR-04 | Venue | Organizer creates a venue with name, city, address and a grid layout (rows x columns) | Must |
| FR-05 | Venue | Organizer assigns a seat category (e.g. Platinum, Gold, Silver) to each row and can mark seats as blocked (aisle, pillar) | Must |
| FR-06 | Event | Organizer creates an event: title, description, venue, start/end time, price per category, max seats per booking | Must |
| FR-07 | Event | Publishing an event generates one `show_seat` row per bookable seat; a published event's layout and prices are locked | Must |
| FR-08 | Discovery | Customer sees a list of upcoming published events with search by title and filter by city/date | Must |
| FR-09 | Seat map | Customer sees the seat grid with each seat's state (available, held, booked, blocked) and category price | Must |
| FR-10 | Booking | Customer selects up to N seats and starts checkout; the system holds all selected seats for 8 minutes or fails the whole request | Must |
| FR-11 | Booking | Checkout page shows seats, price breakup (ticket amount, convenience fee, total) and a live countdown | Must |
| FR-12 | Payment | Backend creates a Razorpay order for the booking and the frontend opens Razorpay Checkout (test mode) | Must |
| FR-13 | Payment | Backend verifies the Razorpay signature and confirms the booking; the `payment.captured` webhook confirms it too, idempotently | Must |
| FR-14 | Payment | If payment succeeds after the hold expired and a seat was taken, the system refunds automatically and marks the booking FAILED\_REFUNDED | Must |
| FR-15 | Ticket | Confirmed booking issues one ticket per seat with a signed QR token; customer sees tickets under My Bookings | Must |
| FR-16 | Check-in | Gate staff open a scanner page, scan a QR with the phone camera and see VALID / ALREADY USED / WRONG EVENT / INVALID | Must |
| FR-17 | Check-in | Check-in is atomic: a ticket can be marked USED only once | Must |
| FR-18 | Organizer | Organizer dashboard shows per event: seats sold, seats held, revenue, checked-in count | Must |
| FR-19 | Organizer | Organizer cancels an event; all confirmed bookings are refunded via Razorpay and tickets invalidated | Should |
| FR-20 | Notification | Booking confirmation email with ticket QR (Mailtrap / Resend sandbox) | Should |
| FR-21 | Booking | Customer can release a hold early ("Change seats") | Should |
| FR-22 | Seat map | Seat map refreshes availability every 5 seconds while open (polling) | Should |
| FR-23 | Admin | Admin creates organizer accounts and views all bookings, payments and refunds | Should |
| FR-24 | Audit | Every booking, payment, refund and check-in state change is written to an audit log | Should |

## 6. Business rules

The rules below are enforced in the backend service layer; the frontend repeats them only for user feedback. Values marked configurable live in environment settings.

| ID | Rule | Value |
| --- | --- | --- |
| BR-01 | A seat can be held or booked by only one booking at a time | Enforced by row lock + partial unique index |
| BR-02 | Seat hold duration | 8 minutes (configurable) |
| BR-03 | A hold covers all requested seats or none | All-or-nothing in one transaction |
| BR-04 | Maximum seats per booking | Set per event, default 6, hard cap 10 |
| BR-05 | A customer can have only one active hold per event | New hold request returns the existing one |
| BR-06 | Booking is allowed only for PUBLISHED events whose start time is in the future | Sales close 30 minutes before start (configurable) |
| BR-07 | Price is fixed per seat category at publish time | Price snapshot stored on the booking line |
| BR-08 | Convenience fee | Flat Rs 30 per ticket + 18% GST on the fee, shown as a separate line before payment |
| BR-09 | Amounts are stored and sent to Razorpay in paise (integers) | No floating-point money |
| BR-10 | A booking is CONFIRMED only after a verified payment (signature or webhook) | Never on the client's word alone |
| BR-11 | Customers cannot cancel confirmed bookings | Matches the live-event norm in Section 2 |
| BR-12 | If the organizer cancels an event, every confirmed booking gets a full refund including the convenience fee, to the original payment method | Razorpay refund API |
| BR-13 | Layout and prices cannot change once an event is published | Organizer must cancel and recreate |
| BR-14 | One QR per seat; a ticket can be checked in once | Atomic conditional update |
| BR-15 | Check-in allowed from 3 hours before start until event end | Configurable window |
| BR-16 | Gate staff can only check in tickets for events they are assigned to | Ownership check |
| BR-17 | QR payload is signed by the server; any tampered or unknown token is INVALID | HMAC-SHA256 or JWT |
| BR-18 | Webhook and verify calls are idempotent: processing the same payment twice changes nothing | Unique `razorpay_payment_id` |

## 7. Exception scenarios

Each exception has a defined system response and an automated test; EX-01 to EX-06 are the ones shown in the demo.

| ID | Scenario | System response | HTTP / state |
| --- | --- | --- | --- |
| EX-01 | Two users request the same seat at the same moment | First transaction wins; second gets "Seat no longer available" and the seat map refreshes | 409 SEAT\_UNAVAILABLE |
| EX-02 | One of several selected seats is already taken | Whole hold rejected, none of the seats held; response lists the taken seats | 409, no partial hold |
| EX-03 | Hold expires before the user pays | Seats show as available to others; checkout page shows "Time expired" and returns to seat map | Booking EXPIRED |
| EX-04 | Payment succeeds after hold expired and seat was taken | Automatic full refund via Razorpay; user sees "Booking failed, refund initiated" | Booking FAILED\_REFUNDED |
| EX-05 | Payment succeeds after hold expired but seats still free | Re-acquire the same seats in one transaction and confirm the booking | Booking CONFIRMED |
| EX-06 | Same QR scanned twice | Second scan shows ALREADY USED with first check-in time and gate user | 409 ALREADY\_USED |
| EX-07 | Payment fails or user closes Razorpay modal | Booking stays PENDING\_PAYMENT; user can retry within the hold window | No state change |
| EX-08 | Duplicate webhook or verify call for the same payment | Ignored after first processing | 200, idempotent |
| EX-09 | Webhook with invalid signature | Rejected and logged | 400 |
| EX-10 | Tampered client: verify call with forged signature | Rejected; booking not confirmed | 400 PAYMENT\_VERIFICATION\_FAILED |
| EX-11 | Webhook never arrives (local dev, network issue) | Client-side verify confirms; a reconcile endpoint fetches order status from Razorpay | Booking CONFIRMED |
| EX-12 | QR for a different event or a cancelled event | WRONG EVENT or CANCELLED shown to gate staff | 422 |
| EX-13 | Forged or malformed QR | INVALID | 400 |
| EX-14 | Scan outside the check-in window | TOO EARLY / EVENT ENDED | 422 |
| EX-15 | Customer requests more seats than allowed | Validation error before any lock is taken | 422 MAX\_SEATS\_EXCEEDED |
| EX-16 | Booking attempt after sales close or on a draft/cancelled event | Rejected | 422 SALES\_CLOSED |
| EX-17 | Organizer cancels an event with confirmed bookings | Refund every confirmed booking; tickets marked CANCELLED; failures listed for manual retry | Event CANCELLED |
| EX-18 | Razorpay refund API call fails | Refund row saved as FAILED with error; admin can retry using the same idempotency key | Refund FAILED |
| EX-19 | Expired or invalid JWT | 401; frontend redirects to login | 401 |
| EX-20 | Customer opens organizer or scanner route | 403 from API; frontend shows "Not authorized" | 403 |

## 8. Non-functional requirements

Targets are sized for a demo deployment on free-tier hosting, not production traffic; each has a way to verify it.

| ID | Category | Requirement | How verified |
| --- | --- | --- | --- |
| NFR-01 | Correctness | Zero double bookings under concurrent requests | pytest: 20 parallel holds on one seat, exactly 1 succeeds |
| NFR-02 | Consistency | Seat, booking and payment state change in one DB transaction | Code review + integration tests |
| NFR-03 | Performance | Seat map and hold APIs respond in under 300 ms at 50 concurrent users | Locust or k6 smoke run |
| NFR-04 | Security | Passwords bcrypt-hashed; JWT expiry 60 min; secrets only in env variables | Code review, `.env.example` |
| NFR-05 | Security | Razorpay checkout signature and webhook signature verified with HMAC-SHA256 | Unit tests |
| NFR-06 | Security | QR tokens signed; no personal data inside the QR | Unit tests |
| NFR-07 | Security | Input validated with Pydantic; SQL only through SQLAlchemy (no string queries); CORS limited to the frontend origin | Code review |
| NFR-08 | Reliability | Payment handlers idempotent; refunds use an idempotency key | Tests EX-08, EX-18 |
| NFR-09 | Usability | Seat map and scanner work on a 360 px wide phone screen | Manual check on phone |
| NFR-10 | Usability | Every error shows a clear message; API errors use one JSON shape `{code, message, details}` | Tests + UI review |
| NFR-11 | Observability | Structured JSON logs with request id; audit log for money and seat state changes | Log review |
| NFR-12 | Maintainability | Layered backend (routers, services, repositories); typed code; lint (ruff, ESLint) passes | CI lint step |
| NFR-13 | Testability | Backend service-layer test coverage of at least 70% | pytest-cov report |
| NFR-14 | Portability | Whole stack starts with `docker compose up` | Fresh clone test |
| NFR-15 | Deployability | Public HTTPS URL for frontend and API | Live demo link |
| NFR-16 | Data | Database schema managed with Alembic migrations; seed script for demo data | Fresh DB test |

## 9. Scope, assumptions and limitations

The MVP covers one complete path from event creation to gate entry; everything else is deliberately excluded so the core path is correct and tested in 5 days.

### 9.1 Included

- Auth with four roles and ownership checks
- Venue grid layout with row categories and blocked seats
- Event create, publish, cancel
- Event list with search and filters
- Seat map, all-or-nothing seat hold with expiry, concurrency-safe booking
- Razorpay test-mode payment, signature verification, webhook, automatic refunds
- Signed QR tickets, mobile camera scanner, atomic check-in
- Organizer dashboard (sold, held, revenue, checked in)
- Booking confirmation email (Should)
- Automated tests, Docker Compose, public deployment

### 9.2 Deliberately excluded

| Excluded | Why | Production approach |
| --- | --- | --- |
| Virtual waiting room / queue | Needed only for very large traffic spikes | Queue service in front of seat-lock API (e.g. Queue-it style) |
| Redis distributed seat locks | Postgres row locks are enough for one DB instance | Redis `SET NX EX` locks + DB unique index as backstop |
| Real-time seat updates via WebSocket | Polling every 5 s is enough for a demo | WebSocket / SSE fan-out |
| Free-form drag-and-drop layout editor, curved or multi-level venues | Takes more than a day of UI work | SVG layout editor |
| General admission (standing) tickets | Different inventory model | Counter-based inventory per zone |
| Movies, multiplexes, multiple shows per event | Event = one show in the MVP | Show entity under event |
| Customer cancellation and partial refunds | Live events usually non-cancellable | Policy engine per event |
| Ticket transfer and resale | Needs ownership transfer and QR reissue | Transfer flow issuing a fresh QR |
| Rotating / time-based QR codes, offline scanning | Static signed QR is enough for the demo | TOTP-style rotating code; offline allow-list sync |
| Coupons, offers, dynamic pricing, loyalty | Not core to the problem statement | Pricing service |
| SMS / WhatsApp notifications | Email covers the integration requirement | SMS gateway |
| Organizer payouts, settlement, GST invoices | Finance flows beyond scope | Razorpay Route / settlements |
| Social login, OTP login, password reset | Email + password is enough | OAuth / OTP provider |
| Multi-language, accessibility audit | Time | i18n, WCAG audit |

### 9.3 Assumptions

- One organizer company per event; venues belong to the organizer who created them.
- An event has exactly one show (one date and time).
- All prices in INR; Razorpay runs in test mode with test cards and UPI test IDs.
- Users have a modern browser; gate staff use a phone with a camera and internet.
- Times stored in UTC, shown in IST.
- Demo data (venues, events, users) comes from a seed script.

### 9.4 Known limitations

- A screenshot of a valid QR works until the real ticket is scanned (first scan wins).
- Polling means a user may see a seat as free for up to 5 seconds after someone else holds it; the hold API still rejects it.
- Webhooks need a public HTTPS URL; on localhost the reconcile endpoint is used instead.
- Free-tier hosting may sleep when idle, so the first request after idle can take 30 to 60 seconds.
- Single database instance; no horizontal scaling or failover.

### 9.5 Stretch backlog and future scope

Excluded features are not dropped: the first seven are stretch items picked in order only after all Must requirements (FR-01 to FR-18) pass and the app is deployed; the rest stay as future scope. Change the Status when an item is picked or finished.

| # | Feature | Est. effort | Builds on | Status |
| --- | --- | --- | --- | --- |
| 1 | Real-time seat updates (Server-Sent Events instead of polling) | 4 to 6 h | Seat map API | Stretch |
| 2 | Customer cancellation with policy-based refund (e.g. full refund until 48 h before) | 4 h | Existing refund service | Stretch |
| 3 | Ticket transfer to another user, issuing a fresh QR | 4 h | `qr_version` on tickets | Stretch |
| 4 | Rotating time-based QR code (refreshes every 30 s) | 3 to 4 h | Signed QR token | Stretch |
| 5 | Coupons and promo codes | 3 h | Price calculation | Stretch |
| 6 | Password reset and email OTP login | 3 h | Auth module, email | Stretch |
| 7 | SMS / WhatsApp booking notification (sandbox) | 2 to 3 h | Notification hook | Stretch |
| 8 | Virtual waiting room for high-demand sales | 2+ days | Seat hold API | Future scope |
| 9 | Redis distributed seat locks | 1 day | Seat hold service | Future scope |
| 10 | Drag-and-drop layout editor, curved and multi-level venues | 2+ days | Venue model | Future scope |
| 11 | General admission (standing) tickets | 1 day | Event and pricing model | Future scope |
| 12 | Multiple shows per event, movie listings | 1 to 2 days | Event model | Future scope |
| 13 | Resale marketplace | 2+ days | Ticket transfer | Future scope |
| 14 | Event recommendations | 1 to 2 days | Booking history | Future scope |
| 15 | Dynamic pricing and loyalty points | 2+ days | Pricing service | Future scope |
| 16 | Offline scanning with allow-list sync | 1 to 2 days | Check-in API | Future scope |
| 17 | Organizer payouts, settlement and GST invoices | 2+ days | Payments | Future scope |
| 18 | Social login (Google) | 4 h | Auth module | Future scope |
| 19 | Multi-language UI | 1 day | Frontend | Future scope |
| 20 | Accessibility (WCAG) audit and fixes | 1 day | Frontend | Future scope |

Effort figures are rough estimates for one developer with Claude Code; re-estimate before picking an item.

## 10. High-level design (HLD)

The system is three containers: a Next.js web app, a FastAPI service and PostgreSQL. The API is the only component that writes to the database or calls Razorpay, so every money and seat decision happens in one place.

&#91;embedded content: system architecture · web, API, database, 2 external services\]

The browser talks to Razorpay only to show the checkout modal; the order it pays for is always created, verified and refunded by the API.

### 10.1 Tech stack

| Layer | Choice | Why |
| --- | --- | --- |
| Frontend | Next.js 15 (App Router), TypeScript, Tailwind CSS, TanStack Query | Matches team skills; middleware for role routes |
| QR scanning | `html5-qrcode` | Camera scanning in mobile browser, no app install |
| Backend | FastAPI, Python 3.12, Pydantic v2 | Typed validation, auto OpenAPI docs |
| ORM / migrations | SQLAlchemy 2.0, Alembic | Explicit transactions and `SELECT ... FOR UPDATE` |
| Database | PostgreSQL 16 | Row-level locks, partial unique indexes, JSON support |
| Auth | JWT (HS256) via `python-jose` / `pyjwt`, bcrypt via `passlib` | Stateless, role in claims |
| Payments | Razorpay Python SDK, test mode | Indian gateway with full sandbox |
| QR generation | `qrcode` + HMAC signing | Signed, tamper-evident tokens |
| Tests | pytest, httpx, Vitest, Playwright | Covers API, concurrency, UI |
| Packaging | Docker, Docker Compose | One-command local stack |

### 10.2 Backend structure

```text
api/
  app/
    main.py            # FastAPI app, CORS, error handlers
    core/              # config, security (JWT, bcrypt), deps (current_user, require_role)
    models/            # SQLAlchemy models
    schemas/           # Pydantic request/response models
    routers/           # auth, venues, events, holds, payments, checkin, organizer, admin
    services/          # booking_service, payment_service, ticket_service, refund_service
    repositories/      # DB queries, including locking queries
    integrations/      # razorpay_client, email_client
  alembic/
  tests/
```

Routers only parse input and call services; services own transactions and business rules; repositories hold SQL. This keeps the locking logic in one file that is easy to review.

### 10.3 Deployment

| Component | Local | Hosted demo |
| --- | --- | --- |
| Web | `web` container (Next.js) | Vercel |
| API | `api` container (Uvicorn) | Render or Railway (Docker deploy) |
| Database | `db` container (Postgres 16) | Neon or Render Postgres |
| Webhook URL | ngrok tunnel (optional) | `https://<api-host>/api/v1/payments/webhook` |
| Secrets | `.env` (not committed) | Platform environment variables |

If separate hosting causes trouble, the fallback is one small VM running the same `docker-compose.yml` behind Caddy for HTTPS. In production the customer and admin apps could be split; for the MVP one app with role routes is enough.

## 11. Low-level design (LLD)

Double booking is prevented by three layers: a row lock while seats are held, a state check when payment is confirmed, and a partial unique index that the database enforces even if application code is wrong.

### 11.1 Data model

| Table | Key columns | Notes |
| --- | --- | --- |
| users | id, name, email (unique), phone, password\_hash, role | role: CUSTOMER, ORGANIZER, GATE\_STAFF, ADMIN |
| venues | id, organizer\_id, name, city, address, rows, cols | Owned by one organizer |
| venue\_seats | id, venue\_id, row\_label, col\_no, category, is\_blocked | Unique (venue\_id, row\_label, col\_no) |
| events | id, organizer\_id, venue\_id, title, description, starts\_at, ends\_at, status, max\_seats\_per\_booking, sales\_close\_at | status: DRAFT, PUBLISHED, CANCELLED, COMPLETED |
| event\_prices | event\_id, category, price\_paise | PK (event\_id, category) |
| show\_seats | id, event\_id, venue\_seat\_id, category, price\_paise, status, booking\_id, hold\_expires\_at | One row per seat per event; unique (event\_id, venue\_seat\_id) |
| bookings | id, user\_id, event\_id, status, ticket\_paise, fee\_paise, total\_paise, hold\_expires\_at, confirmed\_at | See state machine below |
| booking\_seats | booking\_id, show\_seat\_id, price\_paise | Seats requested by the booking; kept after expiry for history |
| payments | id, booking\_id, razorpay\_order\_id (unique), razorpay\_payment\_id (unique), amount\_paise, status | status: CREATED, CAPTURED, FAILED |
| refunds | id, payment\_id, razorpay\_refund\_id, amount\_paise, reason, status, idempotency\_key (unique), error | status: PENDING, PROCESSED, FAILED |
| tickets | id, booking\_id, show\_seat\_id, qr\_version, status, checked\_in\_at, checked\_in\_by | status: VALID, USED, CANCELLED |
| event\_staff | event\_id, user\_id | Gate staff assignment |
| webhook\_events | razorpay\_event\_id (unique), type, payload, processed\_at | Webhook idempotency |
| audit\_logs | id, actor\_id, entity, entity\_id, action, data, created\_at | Money and seat state changes |

Relationships: an organizer owns venues and events; a venue has many venue\_seats; an event has one show\_seat per bookable venue\_seat; a booking has many booking\_seats, one or more payments and, once confirmed, one ticket per seat.

**Database backstop for double booking**

```sql
-- A seat can have at most one live ticket, whatever the application does
CREATE UNIQUE INDEX uq_ticket_live_seat
  ON tickets (show_seat_id)
  WHERE status <> 'CANCELLED';
```

### 11.2 State machines

&#91;embedded content: booking and seat state machines · 5 booking states, 3 seat states\]

A PENDING\_PAYMENT booking becomes EXPIRED lazily: whenever a hold or confirm touches its seats and `hold_expires_at < now()`. No background job is needed for correctness; an optional cleanup task every minute only tidies statuses.

### 11.3 Seat hold algorithm

```sql
BEGIN;
-- 1. Lock the requested seats in a fixed order (prevents deadlocks)
SELECT id, status, booking_id, hold_expires_at
FROM show_seats
WHERE event_id = :event_id AND id = ANY(:seat_ids)
ORDER BY id
FOR UPDATE;

-- 2. In Python: every row must exist and be
--    status = 'AVAILABLE'  OR  (status = 'HELD' AND hold_expires_at < now())
--    otherwise ROLLBACK and return 409 SEAT_UNAVAILABLE with the taken seat ids

-- 3. Create the booking and take the hold
INSERT INTO bookings (...) VALUES (... 'PENDING_PAYMENT', now() + interval '8 minutes');
INSERT INTO booking_seats (...);
UPDATE show_seats
   SET status = 'HELD', booking_id = :booking_id, hold_expires_at = now() + interval '8 minutes'
 WHERE id = ANY(:seat_ids);
COMMIT;
```

After commit, the service creates the Razorpay order (a network call, so it is kept outside the locked transaction) and stores it in `payments`. If order creation fails, the hold is released and the user sees a retry message.

Why this is safe: two transactions asking for the same seat both reach `FOR UPDATE`; Postgres makes the second wait until the first commits, and the second then sees `status = 'HELD'` and fails. Locking all rows in `id` order means two users holding overlapping sets cannot deadlock.

### 11.4 Payment confirmation algorithm

Both `POST /payments/verify` and the `payment.captured` webhook call the same `confirm_booking(order_id, payment_id)` function.

1. Verify the HMAC signature (checkout signature or `X-Razorpay-Signature` for webhooks); reject on mismatch.
2. `BEGIN`; lock the booking row `FOR UPDATE`. If it is already CONFIRMED or FAILED\_REFUNDED, return the stored result (idempotent).
3. Lock the booking's show\_seats `ORDER BY id FOR UPDATE`.
4. If every seat is still held by this booking, or is free again (AVAILABLE, or HELD by an expired booking): set seats BOOKED, booking CONFIRMED, payment CAPTURED, create one ticket per seat. `COMMIT`.
5. Otherwise: release any seats still held by this booking, set booking FAILED\_REFUNDED, insert a PENDING refund row with key `refund-{booking_id}`. `COMMIT`.
6. After commit, call the Razorpay refund API with the idempotency header and update the refund row; send the confirmation email for confirmed bookings.

### 11.5 Booking sequence (happy path)

1. Customer selects seats; web calls `POST /events/{id}/holds`.
2. API runs the hold transaction, creates the Razorpay order, returns `booking_id`, `order_id`, amounts and `hold_expires_at`.
3. Web opens Razorpay Checkout with the `order_id` and `timeout` = seconds left on the hold.
4. Customer pays with a test card or UPI test ID; Razorpay returns `payment_id`, `order_id`, `signature` to the web app.
5. Web calls `POST /payments/verify`; API runs `confirm_booking` and returns tickets.
6. Razorpay sends `payment.captured` to the webhook; API finds the booking already confirmed and returns 200 without changes.
7. Web shows the tickets with QR codes; email is sent.

### 11.6 Check-in algorithm

```sql
-- after verifying the QR signature and that staff is assigned to the event
UPDATE tickets
   SET status = 'USED', checked_in_at = now(), checked_in_by = :staff_id
 WHERE id = :ticket_id AND status = 'VALID'
RETURNING id;
```

One row back means VALID and admitted. Zero rows means the API reads the ticket once more to explain why: ALREADY USED (with time), CANCELLED, or not found. Because the condition and the update are one statement, two gates scanning the same ticket at the same moment cannot both admit it.

## 12. API contracts

All endpoints live under `/api/v1`, use JSON, and return errors as `{"code": "SEAT_UNAVAILABLE", "message": "...", "details": {...}}`. FastAPI generates the full OpenAPI spec at `/docs`.

| Method | Path | Role | Purpose |
| --- | --- | --- | --- |
| POST | /auth/register | Public | Customer sign-up |
| POST | /auth/login | Public | Returns `access_token`, `role` |
| GET | /auth/me | Any | Current user |
| POST | /venues | Organizer | Create venue with layout |
| GET | /venues | Organizer | List own venues |
| GET | /venues/{id} | Organizer | Venue with seat grid |
| POST | /events | Organizer | Create draft event |
| PATCH | /events/{id} | Organizer | Edit draft |
| POST | /events/{id}/publish | Organizer | Publish, generate show seats |
| POST | /events/{id}/cancel | Organizer | Cancel and refund all bookings |
| GET | /events | Public | List published events (`q`, `city`, `from`, `to`, `page`) |
| GET | /events/{id} | Public | Event details and category prices |
| GET | /events/{id}/seats | Public | Seat map with states |
| POST | /events/{id}/holds | Customer | Hold seats, create booking + Razorpay order |
| DELETE | /bookings/{id}/hold | Customer | Release hold early |
| POST | /payments/verify | Customer | Verify checkout signature, confirm booking |
| POST | /payments/webhook | Razorpay | Signed webhook receiver |
| POST | /bookings/{id}/reconcile | Customer | Fetch order status from Razorpay if webhook missed |
| GET | /bookings/me | Customer | My bookings |
| GET | /bookings/{id} | Customer (own) | Booking with tickets and QR |
| POST | /checkin | Gate Staff / Organizer | Validate QR token, mark ticket used |
| GET | /organizer/events/{id}/stats | Organizer | Sold, held, revenue, checked in |
| POST | /events/{id}/staff | Organizer | Assign gate staff |
| GET | /admin/bookings | Admin | All bookings, payments, refunds |
| POST | /admin/users | Admin | Create organizer / staff accounts |
| POST | /admin/refunds/{id}/retry | Admin | Retry a failed refund |

### 12.1 Key payloads

**Hold seats** `POST /events/{id}/holds`

```json
// request
{ "seat_ids": ["b1f...", "c27..."] }
// 201 response
{
  "booking_id": "9a1...",
  "status": "PENDING_PAYMENT",
  "hold_expires_at": "2026-10-28T10:08:00Z",
  "amount": { "tickets": 300000, "fee": 7080, "total": 307080, "currency": "INR" },
  "razorpay": { "order_id": "order_Q1...", "key_id": "rzp_test_..." }
}
// 409 response
{ "code": "SEAT_UNAVAILABLE", "message": "Some seats are no longer available", "details": { "seat_ids": ["c27..."] } }
```

**Verify payment** `POST /payments/verify`

```json
{ "booking_id": "9a1...", "razorpay_order_id": "order_Q1...", "razorpay_payment_id": "pay_R8...", "razorpay_signature": "9ef4..." }
// 200: { "status": "CONFIRMED", "tickets": [ { "id": "...", "seat": "C-7", "qr_token": "..." } ] }
// 200: { "status": "FAILED_REFUNDED", "refund_id": "rfnd_..." }
```

**Check in** `POST /checkin`

```json
{ "qr_token": "eyJ...", "event_id": "e42..." }
// 200: { "result": "VALID", "seat": "C-7", "category": "Gold", "holder": "V. W." }
// 409: { "code": "ALREADY_USED", "details": { "checked_in_at": "2026-10-30T13:02:11Z" } }
```

## 13. Third-party integrations

Razorpay in test mode is the primary, meaningful integration: it covers order creation, checkout, signature verification, webhooks and refunds. Email and QR libraries are secondary.

| Integration | Purpose | Mode | Priority |
| --- | --- | --- | --- |
| [Razorpay Orders + Standard Checkout](https://razorpay.com/docs/developer-tools/integrations/standard-checkout/) | Take payment for a booking | Test keys (`rzp_test_...`) | Must |
| [Razorpay Webhooks](https://razorpay.com/docs/payments/payment-gateway/web-integration/hosted/best-practices.md) | Server-to-server payment confirmation | Test mode, needs public HTTPS | Must |
| [Razorpay Refunds API](https://razorpay.com/docs/api/refunds/create-normal.md) | Late-payment and event-cancellation refunds | Test mode | Must |
| Email (Mailtrap sandbox or Resend) | Booking confirmation with QR | Sandbox | Should |
| `qrcode` (Python) + `html5-qrcode` (browser) | Generate and scan QR tickets | Library | Must |

### 13.1 Razorpay rules we follow

- **Create an order on the server for every payment.** Razorpay auto-refunds payments made without an order id, so checkout always starts from our backend ([Razorpay Custom Checkout](https://razorpay.com/docs/developer-tools/integrations/custom-checkout/)).
- **Verify the checkout signature server-side.** It is HMAC-SHA256 of `order_id|payment_id` using the key secret; only a match proves the payment is authentic ([Razorpay Standard Checkout](https://razorpay.com/docs/developer-tools/integrations/standard-checkout/)).
- **Orders do not expire on their own.** Expiry is controlled with the checkout `timeout` option, so we set it to the remaining hold time ([Razorpay Standard Checkout](https://razorpay.com/docs/developer-tools/integrations/standard-checkout.md)).
- **Use webhooks as the fallback for dropped callbacks.** Razorpay recommends `payment.captured`, `payment.failed` and `order.paid`, and checking that the payment is captured before giving the service ([Razorpay best practices](https://razorpay.com/docs/payments/payment-gateway/web-integration/hosted/best-practices.md)). Webhooks reach only public HTTPS URLs, so local testing needs a tunnel or the deployed API.
- **Refunds are idempotent.** The refund call carries an `X-Refund-Idempotency` header (at least 10 characters); normal-speed refunds take 5 to 7 working days in live mode ([Razorpay idempotent refunds](https://razorpay.com/docs/api/refunds/normal-refunds-idempotent/?preferred-country=IN)). We use `refund-{booking_id}` as the key.
- **Money in paise.** Rs 500 is sent as `50000`.

### 13.2 QR token design

- Payload: `{tid: ticket_id, eid: event_id, v: 1}`, signed with HMAC-SHA256 using a server secret (or a JWT with HS256), base64url encoded.
- No name, phone or email inside the QR.
- Scanner sends the raw token to `POST /checkin`; the server checks the signature, then the database state. The signature stops forgery; the database stops reuse.
- Ticket reissue (future transfer feature) bumps `v`, so older QR codes fail.

## 14. Testing strategy

Testing concentrates on the parts where a bug costs money or a seat: holds, payments, refunds and check-in. Backend tests run against a real Postgres container, because row locks cannot be tested on SQLite.

| Level | Tool | What it covers |
| --- | --- | --- |
| Unit | pytest | Price and fee calculation, QR sign/verify, Razorpay signature verify, state transitions |
| Integration | pytest + httpx + Postgres (testcontainers or compose) | API endpoints, RBAC (401/403), validation errors, DB constraints |
| Concurrency | pytest + asyncio / thread pool | 20 parallel holds on one seat: exactly 1 success, 19 x 409 |
| Payment | pytest with mocked Razorpay client | Verify success, forged signature, duplicate webhook, late payment refund |
| Frontend | Vitest + React Testing Library | Seat selection limits, countdown, checkout states |
| End to end | Playwright (one happy path) | Sign up, hold, pay with test card, see QR |
| Manual | Razorpay test cards / UPI, two browsers, phone camera | Real checkout, two-user race, scanning |

### 14.1 Must-have test cases

- [ ] Concurrent hold on the same seat: one winner (EX-01)
- [ ] Partial overlap rejects whole hold (EX-02)
- [ ] Expired hold frees seats (EX-03)
- [ ] Late payment with seat taken triggers refund (EX-04)
- [ ] Late payment with seat free confirms (EX-05)
- [ ] Double scan returns ALREADY\_USED (EX-06)
- [ ] Duplicate webhook is a no-op (EX-08)
- [ ] Forged checkout signature rejected (EX-10)
- [ ] Customer cannot call organizer or check-in APIs (EX-20)
- [ ] Max seats per booking enforced (EX-15)
- [ ] Event cancel refunds all confirmed bookings (EX-17)
- [ ] Fee and GST calculation in paise

## 15. Delivery plan and risks

The full booking path must work end to end by the end of Day 3 (Wed 28 Oct); Days 4 and 5 add payments edge cases, polish, tests and documents. Senior time is used twice, at the two points where a review changes the most.

| Day | Date | Work | Exit criterion | Senior check-in |
| --- | --- | --- | --- | --- |
| 1 | Mon 26 Oct | Research, this requirements and design document, repo setup, `docker compose` skeleton | Document reviewed; `web`, `api`, `db` containers start | 30 min: review LLD, seat-hold design and scope |
| 2 | Tue 27 Oct | Backend: auth + RBAC, models + Alembic, venue, event, publish, seat map, hold logic, concurrency test; deploy hello-world API and web | Concurrency test passes; API live on public URL | None |
| 3 | Wed 28 Oct | Frontend: login, event list, seat map, checkout with countdown, My Bookings, organizer pages | Hold to confirmed booking works with Razorpay test card | None |
| 4 | Thu 29 Oct | Razorpay webhook, late-payment refund, event cancel refunds, QR tickets, scanner page, email, error states | All Must FRs done; webhook works on deployed API | 30 min: demo walkthrough and test gaps |
| 5 | Fri 30 Oct | Remaining tests, coverage, final deploy, assumptions doc, AI review report, demo script and rehearsal | Live demo URL, all deliverables submitted | Optional |

### 15.1 Deliverables checklist

- [ ] Requirements and design document (this document)
- [ ] Source code repository with README and `.env.example`
- [ ] Dockerfiles + `docker-compose.yml`
- [ ] Deployed frontend and API URLs
- [ ] Test report (pytest + coverage, Vitest)
- [ ] Assumptions, limitations and exclusions (Section 9)
- [ ] AI review report: Claude reviews this document, the code and the tests in a separate session; findings, accepted fixes and rejected suggestions recorded with reasons
- [ ] Demo script and recording

### 15.2 Risks

| Risk | Impact | Mitigation | Cut-line if late |
| --- | --- | --- | --- |
| Razorpay webhook cannot reach localhost | Payments not confirmed in dev | Use verify endpoint locally; test webhook on deployed API; ngrok as fallback | Rely on verify + reconcile |
| Deployment issues (CORS, env vars, DB URL) | Day 5 lost | Deploy hello-world on Day 2 | Demo on local Docker + screen recording |
| Seat map UI takes too long | Day 3 slips | Plain CSS grid, no drag-and-drop | Fixed demo layout |
| AI-generated code with subtle locking bugs | Double booking in demo | Read every line of hold/confirm code; concurrency test first | None: this is not cut |
| Free-tier cold start during demo | Slow first request | Warm up URLs 5 minutes before demo | Local fallback |
| Scope creep | Core path unfinished | Only Must FRs until Day 3 end | Drop FR-19 to FR-24 in order |

## 16. Sources

- [Zomato to acquire Paytm's entertainment ticketing business for Rs 2,048 cr](https://www.theweek.in/wire-updates/business/2024/08/21/del88-biz-ld-paytm-zomato.html) (The Week / PTI)
- [India's Zomato expands ticketing with $244m Paytm deal](https://dealstreetasia.com/?p=409437) (DealStreetAsia)
- [Zomato aims to launch District app within weeks](https://www.theticketingbusiness.com/?p=92259) (The Ticketing Business)
- [District isn't even 2% of Eternal's business](https://the-ken.com/story/district-isnt-even-2-of-eternals-business-but-its-enough-to-rattle-bookmyshow/) (The Ken)
- [IPL 2025 M-tickets guide](https://mumbaiindians.com/news/ipl-2025-m-tickets-guide-mumbai-indians-cricket) (Mumbai Indians)
- [Internet handling fee under scrutiny](https://www.deccanherald.com/amp/story/india%2Fkarnataka%2Fbengaluru%2Finternet-handling-fee-under-scrutiny-731842.html) (Deccan Herald)
- [BookMyShow may exit Maharashtra over convenience fee](https://www.medianama.com/2013/09/223-bookmyshow-may-exit-maharashtra-if-convenience-fee-issue-isnt-resolved/) (MediaNama)
- [BookMyShow complaints: payment debited, no tickets](https://voxya.com/consumer-complaints/payment-debited-but-no-tickets-received/267527) (Voxya)
- [bookmyshow.com reputation summary](https://tools.malwaretips.com/url-scan/bookmyshow.com) (MalwareTips)
- [Ticketmaster Smart Queue](https://business.ticketmaster.com/smart-queue/) (Ticketmaster Business)
- [SafeTix rotating barcode FAQ](https://www.nba.com/hawks/managetickets) (Atlanta Hawks)
- [Ticketmaster puts an end to screenshots](https://techcrunch.com/2019/05/16/ticketmaster-put-an-end-to-screenshots-with-new-digital-ticket-technology/amp/) (TechCrunch)
- [LLD: Movie Ticket Booking System](https://techinterview.org/lld-movie-ticket-booking/) (TechInterview)
- [Razorpay Standard Checkout integration](https://razorpay.com/docs/developer-tools/integrations/standard-checkout/)
- [Razorpay Custom Checkout integration](https://razorpay.com/docs/developer-tools/integrations/custom-checkout/)
- [Razorpay payment gateway best practices](https://razorpay.com/docs/payments/payment-gateway/web-integration/hosted/best-practices.md)
- [Razorpay create normal refund](https://razorpay.com/docs/api/refunds/create-normal.md)
- [Razorpay idempotent refunds](https://razorpay.com/docs/api/refunds/normal-refunds-idempotent/?preferred-country=IN)

Platform internals (BookMyShow and District lock durations, queue behaviour) are not public; statements about them are based on visible app behaviour and common industry design, not official documentation.
