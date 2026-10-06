# The Pandit — Consolidated Requirements Document

**Version:** 3.0 (Consolidated & Enhanced)
**Date:** July 2026
**Sources:** Requirement Specifications v2.0, Architecture v1.1, Addendum A (Pandit Services Marketplace), Addendum B (Pooja Items Marketplace)
**Review Perspectives:** Sr Product Manager, Sr Enterprise Architect, Lead Developer

---

## Executive Summary

This document consolidates all requirements from the four source documents into a single, prioritized, module-organized specification. It incorporates critique and improvements from three expert perspectives and serves as the definitive requirements reference for the build team.

**The Pandit** is a Hindu Panchang, calendar, planning, and spiritual-lifestyle platform spanning mobile (iOS/Android), responsive web, and admin console — augmented by two embedded marketplaces (Pandit services and Pooja items).

---

## Table of Contents

1. [Product Vision & Objectives](#1-product-vision--objectives)
2. [Target Audience](#2-target-audience)
3. [Module 1: Panchang Engine (CRITICAL)](#3-module-1-panchang-engine-critical)
4. [Module 2: Calendar & Views](#4-module-2-calendar--views)
5. [Module 3: Festival & Vrat System](#5-module-3-festival--vrat-system)
6. [Module 4: Notes, Bookmarks & Reminders](#6-module-4-notes-bookmarks--reminders)
7. [Module 5: Muhurat & Auspicious Planning](#7-module-5-muhurat--auspicious-planning)
8. [Module 6: Hindu Life Planner](#8-module-6-hindu-life-planner)
9. [Module 7: Family Features](#9-module-7-family-features)
10. [Module 8: Printable Calendar System](#10-module-8-printable-calendar-system)
11. [Module 9: AI Assistant — Ask The Pandit](#11-module-9-ai-assistant--ask-the-pandit)
12. [Module 10: Search & Discovery](#12-module-10-search--discovery)
13. [Module 11: User Management & Auth](#13-module-11-user-management--auth)
14. [Module 12: Subscription & Billing](#14-module-12-subscription--billing)
15. [Module 13: Notifications](#15-module-13-notifications)
16. [Module 14: Content Management System](#16-module-14-content-management-system)
17. [Module 15: Admin Panel](#17-module-15-admin-panel)
18. [Module 16: Pandit Services Marketplace](#18-module-16-pandit-services-marketplace)
19. [Module 17: Pooja Items Marketplace](#19-module-17-pooja-items-marketplace)
20. [Module 18: Sharing, Export & Integration](#20-module-18-sharing-export--integration)
21. [Module 19: Widgets & Quick Access](#21-module-19-widgets--quick-access)
22. [Module 20: Advanced Features](#22-module-20-advanced-features)
23. [Non-Functional Requirements](#23-non-functional-requirements)
24. [Security & Privacy](#24-security--privacy)
25. [Subscription Tier Feature Matrix](#25-subscription-tier-feature-matrix)
26. [Data Model](#26-data-model)
27. [Expert Critique & Recommendations](#27-expert-critique--recommendations)

---

## 1. Product Vision & Objectives

### 1.1 Product Name
**The Pandit**

### 1.2 Vision
To create a modern, accurate, beautifully designed Hindu calendar and Panchang app that helps Hindus around the world plan their day, month, and year according to Hindu traditions — augmented by a trusted marketplace for priestly services and pooja supplies.

### 1.3 Mission
Become the default daily-use app for Hindu families by combining:
- Accurate Panchang data & Hindu festival calendar
- Personal planning tools, reminders & notifications
- Ritual guidance & spiritual lifestyle features
- Printable calendars & premium calendar products
- Regional & sampradaya-based customization
- A trusted marketplace for pandit services and pooja items

### 1.4 Platforms
| Platform | Priority | Notes |
|----------|----------|-------|
| Responsive Web App | **Primary (build first)** | Next.js + Tailwind; SEO, discoverability |
| iOS Mobile App | Target | Swift/SwiftUI; widgets, lock-screen |
| Android Mobile App | Target | Kotlin/Jetpack Compose; widgets |
| Tablet Layout | Supported | Responsive design |
| Smart Displays/Widgets | Future | Post-launch consideration |

### 1.5 Core Objectives
1. Show accurate daily Panchang based on user location
2. Provide Hindu calendar views (day, week, month, year, 12–15 month)
3. Enable personal, religious, and family event planning
4. Deliver intelligent reminders for festivals, vrats, muhurats, and personal events
5. Generate printable high-definition calendars
6. Offer subscription-based premium features
7. Connect patrons with verified pandits for ceremonies (marketplace)
8. Provide a curated pooja items marketplace
9. Support global Hindu users with regional calendars, languages, and local calculations

### 1.6 Key Differentiators
- **Tithi-based recurring reminders** — events that recur by lunar calendar, not just Gregorian
- **Festival Rule Engine** — festivals derived from astronomical rules, not hardcoded dates
- **Muhurat Finder** — intelligent auspicious-time discovery
- **HD Printable Calendar Generator** — commercial-grade output
- **Pandit Services Marketplace** — verified priests, escrow payments, live video ceremonies
- **Pooja Items Marketplace** — curated supplies with festival/checklist integration
- **AI Spiritual Assistant** — grounded in CMS content and computed Panchang

---

## 2. Target Audience

### 2.1 Primary Users
- Hindu families worldwide; practising Hindus who follow Panchang daily
- People planning festivals, vrats, pujas, weddings, griha pravesh, namakaran, travel, business activities
- Temple visitors and devotees
- Hindu priests, pandits, astrologers, and spiritual consultants
- Indian diaspora communities and Hindu cultural organizations

### 2.2 Secondary Users
- Calendar publishers, event organizers, wedding planners
- Yoga and spiritual centres, Hindu schools, community groups
- Religious product sellers and astrology practitioners

### 2.3 Marketplace-Specific Personas
| Role | Description |
|------|-------------|
| **Patron** | Silver/Gold subscriber booking a pandit or buying pooja items |
| **Pandit (Provider)** | Verified priest offering ceremonial services |
| **Seller (Merchant)** | Vetted merchant listing pooja items/bundles |
| **Marketplace Ops** | Platform staff managing approvals, disputes, payouts |

> **🔴 PM Critique — Missing Persona:** The documents lack a "Temple Administrator" persona who would manage temple calendars, events, and potentially bulk-order pooja supplies. This should be added for Phase 3.

---

## 3. Module 1: Panchang Engine (CRITICAL)

**Priority:** 🔴 CRITICAL — Foundation for everything else
**Complexity:** Very High

### 3.1 Calculation Engine

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Methodology | Drik Ganita (observational) | Vakya/Surya-Siddhanta drifts hours from observed positions |
| Library | Swiss Ephemeris (~0.001 arcsec precision) | NASA/JPL-derived; de-facto gold standard |
| Ayanamsa | Lahiri (Chitrapaksha) default; user override | Shifts every sidereal position |
| Day Boundary | Sunrise-to-sunrise, per location | Hindu day is not midnight-based |
| Month Scheme | Both Amanta & Purnimanta, user-selectable | Festivals shift by a month between schemes |
| Leap/Skipped Month | Detect & label Adhika/Kshaya maas | Affects festival years |

### 3.2 Licensing
- **Development/Testing:** Free AGPL build — no cost until commercial distribution
- **Commercial Launch:** Astrodienst commercial licence required before App Store/Play Store distribution
- **⚠️ HARD LAUNCH GATE:** Production builds must not ship without the commercial licence

### 3.3 Compute & Cache Strategy
- Panchang is **precomputed and cached**, never calculated on the client device
- Cache key: `date + location_grid + ayanamsa + month_scheme`
- Nearby users share cache entries via location grid rounding
- Warming job precomputes a rolling ≥15-month horizon for popular locations
- On cache miss: compute once → store → return
- All consumers (reminders, festivals, calendar views) read the same cache

### 3.4 Required Output Data
Every daily Panchang must include with precise start/end times:
- Tithi, Nakshatra, Yoga, Karana, Vara (Weekday)
- Paksha, Amanta month, Purnimanta month
- Sunrise, Sunset, Moonrise, Moonset
- Moonsign, Sunsign
- Shaka/Vikram/Gujarati Samvat, Ritu, Ayana, Samvatsara
- Rahu Kalam, Yamaganda, Gulika Kalam
- Abhijit Muhurat, Dur Muhurat, Varjyam, Amrit Kalam
- Brahma Muhurat, Nishita Kaal
- Choghadiya, Hora, Gowri Panchangam (where applicable)

### 3.5 Edge Cases (MUST Handle)
- **Adhika maas** (leap lunar month) and **Kshaya maas** (skipped lunar month)
- **Kshaya tithi** (tithi never spans a sunrise) and **Vriddhi tithi** (tithi spans two sunrises)
- Sunrise undefined at **high latitudes** — graceful fallback
- **DST transitions** occurring mid-tithi
- **24-plus** past-midnight timings as first-class engine values

### 3.6 Accuracy Assurance

#### User Stories
- **US-3.6.1:** As a user, I trust that the Panchang data matches established published Panchangs within agreed tolerance
- **US-3.6.2:** As a developer, I have a CI-integrated validation harness that blocks merges on regressions
- **US-3.6.3:** As an admin, I can review user-flagged accuracy corrections through an editorial workflow

#### Acceptance Criteria
- [ ] Curated reference dataset of known-good Panchang values across dates, locations, and edge cases
- [ ] Engine output asserted against reference within agreed tolerance
- [ ] CI pipeline blocks on any regression
- [ ] User/admin flag-and-review correction workflow operational
- [ ] Validation covers all edge cases (Adhika, Kshaya, DST, high latitude)

> **🔵 Architect Critique:** The spec doesn't define the location grid granularity. Recommend 0.1° lat/lon (~11km) as a starting point — fine enough for accurate sunrise times but coarse enough for cache efficiency. This should be configurable.

> **🟢 Developer Critique:** Swiss Ephemeris is C-based. The wrapping strategy matters: recommend a Python C-extension or Rust FFI binding for the computation service, not a subprocess call. Need to validate that the AGPL build's test-only restrictions are compatible with our CI/CD pipeline.

---

## 4. Module 2: Calendar & Views

**Priority:** 🔴 CRITICAL
**Complexity:** High

### 4.1 Day View
- Full Panchang for selected date
- Previous/next navigation, jump to today
- Add note, add reminder, bookmark, share, print
- View festival/muhurat details
- 12/24/24-plus time format toggle

### 4.2 Week View
- Seven-day Gregorian week with Tithi/Nakshatra per day
- Festival/vrat markers, moon phase
- User notes, reminders, auspicious/inauspicious indicators
- Weekly spiritual planner

### 4.3 Month View
- Gregorian month grid with Hindu date per day
- Tithi markers, festival/vrat labels
- Ekadashi/Purnima/Amavasya/Sankranti/Pradosham/Chaturthi indicators
- Notes, bookmarks, moon-phase icons, user events
- Optional temple events

### 4.4 Year View
- Twelve-month overview
- Major festivals, important vrats, regional holidays
- Solar and lunar events, bookmarks
- Print/export options

### 4.5 12-to-15-Month Calendar View
- Continuous Hindu calendar for next 12–15 months
- Start/end month selection
- Regional calendar type, language, location, festival categories
- Printable HD layout, downloadable PDF, commercial print-ready export
- Served from precomputed Panchang cache (never computed live)

#### User Stories
- **US-4.1:** As a daily user, I open the app and see today's complete Panchang within 2 seconds
- **US-4.2:** As a planner, I can navigate to any date within 15 months and see its full Panchang
- **US-4.3:** As a family member, I can see the month view with all my notes, bookmarks, and festival markers
- **US-4.4:** As a calendar publisher, I can generate a 15-month view with my regional preferences

#### Acceptance Criteria
- [ ] Day view loads within 2 seconds on normal connection
- [ ] All five calendar views functional (day, week, month, year, 12-15 month)
- [ ] Time format toggle (12h/24h/24+) works correctly
- [ ] Navigation between dates is seamless
- [ ] Offline access to current month and recently viewed days

---

## 5. Module 3: Festival & Vrat System

**Priority:** 🔴 CRITICAL
**Complexity:** High

### 5.1 Festival Rule Engine
Each festival encoded as a **rule** over Tithi, Nakshatra, Paksha, lunar/solar month, and month scheme (Amanta vs Purnimanta), with regional variants. A resolver turns rules into concrete occurrences for a given year and location.

**Festival Rule — Required Fields:**
- Festival name and identifier
- Anga rule: tithi/nakshatra/paksha/month/scheme
- Regional variants (which regions observe, per-region rule overrides)
- Deity, significance, and observance window
- Resolution priority for tie-breaks

### 5.2 Festival Content (CMS-Managed)
Per festival: name, governing rule, region, deity, description, significance, puja method, fasting rules, story/katha, mantras, required items, do's and don'ts, related rituals, suggested charity, regional variations.

### 5.3 Festival Detail Page
Overview, why celebrated, when observed, how to perform puja, puja samagri list (→ links to Pooja Items Marketplace), vrat rules, mantras, katha, food recommendations, regional customs, share, add to reminder, add to family calendar, **"Book a Pandit" CTA** (→ links to Pandit Marketplace).

### 5.4 Vrat Tracker
Track: Ekadashi, Pradosham, Sankashti Chaturthi, Purnima vrat, Amavasya rituals, Navratri fasting, Shravan Somvar, Karva Chauth, Maha Shivaratri, Satyanarayan vrat, and custom vrats.

### 5.5 Vrat Completion Tracking
Status: planned, observed, missed, completed. Attach notes and sankalp.

#### User Stories
- **US-5.1:** As a user, I see accurate festival dates derived from astronomical rules, not hardcoded
- **US-5.2:** As a regional user, I see festivals relevant to my region/tradition with correct dates
- **US-5.3:** As a devotee, I can track my vrat commitments and mark completion
- **US-5.4:** As a user viewing a festival page, I can one-tap book a pandit or buy the samagri kit

#### Acceptance Criteria
- [ ] Festival rule engine correctly handles Amanta/Purnimanta month-shift
- [ ] Regional variant festivals display correctly per user preference
- [ ] Vrat tracker allows all status transitions with notes
- [ ] Festival pages integrate with both marketplace CTAs
- [ ] Edge cases (Adhika maas festivals) handled correctly

> **🔴 PM Critique — Missing Feature:** There's no "Festival Countdown" or "Festival Feed" feature — a social/community timeline where users share how they're preparing. This could be a powerful engagement driver for Phase 2.

---

## 6. Module 4: Notes, Bookmarks & Reminders

**Priority:** 🟡 HIGH
**Complexity:** Medium-High

### 6.1 Notes
Add notes to any date: personal events, puja plans, family rituals, travel, temple visits, fasting notes, wedding planning, sankalp details, spiritual goals.

### 6.2 Bookmarks
Categories: festivals, family events, muhurat, vrat, travel, temple visit, personal reminder, important spiritual date, custom categories.

### 6.3 Reminder System
Reminders for: festivals, vrats, puja days, Ekadashi, Pradosham, Sankashti Chaturthi, Purnima, Amavasya, birthdays, anniversaries, custom notes, muhurat start/end, Rahu Kalam warnings, sunrise/sunset-based.

### 6.4 Reminder Timing
At exact time, or 5/15/30 min, 1 hour, 1 day, 3 days, 1 week before, or custom offset.

### 6.5 Recurring Reminders
By: Gregorian date, Hindu Tithi, Nakshatra, weekday, lunar month, solar month, annual festival cycle, monthly vrat cycle.

### 6.6 Tithi-Based Recurrence — Resolution Rules
1. Stored as a **rule** (e.g., "every Kartik Purnima"), not a fixed date
2. Scheduler resolves forward over ≥15-month rolling horizon into fire-times per user location/timezone
3. Resolution reads precomputed Panchang cache
4. **Kshaya tithi:** fires on the day the tithi is current at conventional reference moment per regional convention
5. **Vriddhi tithi:** fires once on the day chosen by regional convention; must not double-fire
6. Location change re-resolves all future fire-times

#### User Stories
- **US-6.1:** As a devotee, I set a reminder for "every Shukla Ekadashi" and it correctly fires on the right day in my location
- **US-6.2:** As a user who moves cities, my Tithi-based reminders automatically adjust to my new location
- **US-6.3:** As a free user, I can create up to 5 notes, 5 bookmarks, and 5 reminders

#### Acceptance Criteria
- [ ] Tithi-based recurrence correctly resolves for kshaya/vriddhi edge cases
- [ ] Location change triggers re-resolution of all future fire-times
- [ ] Reminders, calendar views, and festival dates all agree (same cache source)
- [ ] Free-tier limits enforced (5 notes, 5 bookmarks, 5 reminders)

---

## 7. Module 5: Muhurat & Auspicious Planning

**Priority:** 🟡 HIGH (Premium differentiator)
**Complexity:** High

### 7.1 Muhurat Finder
Find auspicious times for: wedding, engagement, griha pravesh, namakaran, annaprashan, mundan, vidyarambh, vehicle/property purchase, business launch, travel, education, investment, contracts, puja, temple visit, housewarming, bhoomi puja.

### 7.2 Muhurat Filters
- Date range, location, event type
- Avoid Rahu Kalam / Yamaganda / Gulika
- Preferred weekday, Nakshatra, or Tithi
- Family availability, regional rules
- **(Future)** Pandit availability (→ Marketplace integration)

### 7.3 Muhurat Recommendation
Returns best/good/avoid dates with explanation. Calendar save, share with family, export to PDF. Scoring uses the same engine output and avoidance windows as the daily Panchang.

#### User Stories
- **US-7.1:** As a user planning griha pravesh, I find the best date next month that avoids Rahu Kalam and falls on a preferred weekday
- **US-7.2:** As a Gold user, I get AI-assisted muhurat recommendations with detailed explanations
- **US-7.3:** As a user, I can directly book a pandit for my chosen muhurat date

#### Acceptance Criteria
- [ ] Muhurat recommendations consistent with daily Panchang view
- [ ] Filters work correctly including avoidance windows
- [ ] Results exportable to PDF and shareable
- [ ] Deep-link to Pandit marketplace for booking on selected muhurat

---

## 8. Module 6: Hindu Life Planner

**Priority:** 🟡 HIGH (Premium)
**Complexity:** Medium

### 8.1 Daily Spiritual Planner
Today's mantra, deity worship, recommended dana, simple puja, meditation, best japa time, vrat reminders, Rahu Kalam caution, sunrise/sandhya vandanam reminders.

### 8.2 Monthly Spiritual Planner
Major festivals, vrats, good puja days, charity days, family ritual days, temple visit suggestions, spiritual goals, monthly sankalp.

### 8.3 Annual Hindu Planner
Plan festivals, family pujas, pilgrimages, temple donations, vrat calendar, ancestral rituals, shraddha dates, children's samskaras, community participation.

---

## 9. Module 7: Family Features

**Priority:** 🟡 HIGH
**Complexity:** Medium

### 9.1 Family Calendar
Add family members, Gregorian and Tithi-based birthdays, anniversaries, optional gotra/nakshatra, personal vrat preferences, shared notes/reminders, family puja planning.

### 9.2 Hindu Birthday Tracking
By: Gregorian date, Tithi, Nakshatra, lunar month, regional calendar system.

### 9.3 Family Ritual Reminders
Birthdays, marriage anniversaries, annual pujas, shraddha, Tithi-based remembrance days, kuldevata puja, family temple visits.

**Note:** Family member birth details are sensitive data (stored in encrypted vault). Tithi-based family dates resolve through the same scheduler as Module 4.

#### User Stories
- **US-9.1:** As a parent, I track my children's Hindu birthdays (by Tithi and Nakshatra) and get annual reminders
- **US-9.2:** As a family head, I plan the annual Satyanarayan puja and share the plan with all family members
- **US-9.3:** As a user, I maintain shraddha dates and get reminders based on the Hindu calendar

> **🔴 PM Critique:** Family sharing needs a proper invitation/acceptance flow with role-based permissions (admin vs member). The current spec doesn't detail how families are formed or how conflicts are resolved when two family members edit the same event.

---

## 10. Module 8: Printable Calendar System

**Priority:** 🟡 HIGH (Revenue driver)
**Complexity:** High

### 10.1 Calendar Generation Options
- Duration: 12–15 months
- Start month selection
- Region, language, location
- Calendar style, festival categories
- Deity/temple theme
- Premium: family-photo, business, community branding
- Print size, export format

### 10.2 Print Sizes
A4, A3, Letter, Legal, wall, desk, custom dimensions, mobile wallpaper, poster formats.

### 10.3 Output Quality
- High-resolution PDF, 300-DPI print-ready
- Future: CMYK-ready, bleed margins, premium crop marks
- Vector text where possible, HD image support

### 10.4 Templates
Traditional, minimal modern, temple-themed, deity-themed, South/North Indian, Gujarati, corporate gifting, community, family, premium artistic.

### 10.5 Monetization
- Pay-per-calendar download
- Premium templates
- Business/temple/community branded calendars
- Bulk/white-label generation
- Future: print-partner, physical-calendar ordering

**Note:** Generation is asynchronous and queue-driven; large exports never block the interactive app.

---

## 11. Module 9: AI Assistant — Ask The Pandit

**Priority:** 🟢 MEDIUM (Phase 2-3)
**Complexity:** High

### 11.1 Capabilities
- Panchang explainer
- Festival assistant (explanations, puja steps, samagri, vrat rules, regional variations)
- Family-friendly and children's modes
- Premium planning assistant ("find a good date for griha pravesh next month")

### 11.2 Grounding & Safety Rules
- Answers grounded in festival/educational CMS corpus and day's computed Panchang
- **No free-form invention** of ritual instructions
- Every ritual/life-decision answer appends: "consult a qualified pandit, guru, or family tradition"
- Respects content-sensitivity rules: presents regional variation, never asserts one tradition as the only correct one

> **🔵 Architect Critique:** The AI grounding strategy is sound but needs a RAG (Retrieval-Augmented Generation) architecture explicitly defined. Recommend a vector store (Pinecone/Weaviate) indexed on the CMS corpus, with the daily Panchang injected as structured context. Need to define fallback behavior when the AI has no grounded answer.

---

## 12. Module 10: Search & Discovery

**Priority:** 🟡 HIGH
**Complexity:** Medium

Global search across: festivals, dates, tithis, nakshatras, muhurats, vrats, mantras, deities, calendar events, notes, bookmarks.

**Smart queries** (natural language):
- "When is Diwali this year?"
- "Next Ekadashi"
- "Good day for housewarming in July"
- "When is Krishna Janmashtami in Dubai?"

> **🟢 Developer Critique:** Smart queries imply NLU/intent parsing. This should be scoped carefully — either rule-based pattern matching for MVP, or LLM-powered for Gold tier. Don't build a custom NLU; leverage the AI assistant module.

---

## 13. Module 11: User Management & Auth

**Priority:** 🔴 CRITICAL
**Complexity:** Medium

### 13.1 Account Creation
- Email, mobile number, Google login, Apple login
- Optional Facebook login
- Guest mode for free users

### 13.2 User Profile
- Full name, preferred display name
- Date of birth (→ Sensitive Vault)
- Optional time and place of birth (→ Sensitive Vault)
- Current location, preferred language
- Preferred Hindu calendar system
- Optional preferred deity/sampradaya
- Notification preferences, subscription level
- Family members (birth data → Sensitive Vault)

### 13.3 Location Settings
- Automatic detection, manual city selection
- Saved favourite locations
- Travel mode with Panchang recalculation
- Time-zone awareness including DST

### 13.4 Calendar Preferences
- Amanta or Purnimanta
- Vikram, Shaka, or Gujarati Samvat
- Regional calendars: Tamil, Malayalam, Bengali, Telugu, Kannada, Marathi
- North or South Indian style
- Regional festival preferences

### 13.5 Role Composition
A single login may hold multiple roles:
- User (patron/buyer)
- Pandit (service provider)
- Seller (pooja items merchant)
- Admin (with sub-roles)

---

## 14. Module 12: Subscription & Billing

**Priority:** 🔴 CRITICAL
**Complexity:** High

### 14.1 Three Tiers

#### Basic (Free)
- Daily Panchang (current location), basic day/month views
- Major festivals (basic descriptions), basic reminders
- Limited: 5 notes, 5 bookmarks, 5 reminders
- Current-year calendar only, no HD export
- No AI assistant, no family calendar
- Ads may be shown

#### Silver (Paid)
- Ad-free, full week/month/year views
- Unlimited notes, bookmarks, reminders
- Recurring Tithi-based reminders
- Regional festival customization, multiple saved locations
- Festival preparation guides, vrat tracker
- Calendar sync (Google/Apple), PDF export
- Basic 12-month printable calendar, basic muhurat finder
- Limited family profiles (5 members), Hindu birthday tracking
- Widgets, multilingual, cloud sync
- **Book a Pandit** (marketplace access)
- **Pooja Items Marketplace** (buy access)

#### Gold (Premium)
- Everything in Silver, plus:
- Advanced muhurat finder
- AI assistant (Ask The Pandit)
- Personalized Hindu life planner
- 12–15 month HD calendar (300 DPI), premium templates
- Family calendar sharing (unlimited members)
- Business/temple/community calendar generation
- Advanced festival planning, puja samagri checklist
- Vrat completion tracking, annual spiritual planner
- Shraddha/ancestral reminders
- Sankalp journal, mantra tracker
- Priority support, early access
- Multi-device sync, family sharing
- **Reduced marketplace platform fee** (optional Gold perk)

### 14.2 Payment Platforms
- Apple In-App Purchases (iOS subscriptions)
- Google Play Billing (Android subscriptions)
- Stripe (web subscriptions)
- **Separate:** Stripe Connect for marketplace transactions (NOT through IAP)

### 14.3 Receipt Reconciliation
All three subscription sources reconciled server-side into a single Subscription record. Entitlement checks enforced at API gateway, not in client code.

---

## 15. Module 13: Notifications

**Priority:** 🟡 HIGH
**Complexity:** Medium

### 15.1 Types
- Daily Panchang summary, sunrise reminder
- Rahu Kalam warning
- Festival, vrat, puja, muhurat reminders
- Note/birthday reminders, Tithi-based event reminders
- Calendar-print offers, subscription updates
- **Marketplace:** booking confirmations, shipping updates, payout notifications (see Modules 16-17)

### 15.2 Personalization
Users control: timing, categories, festival regions, frequency, quiet hours, language, sound.

### 15.3 Delivery Channels
Push (APNs + FCM), in-app, email, optional SMS.

**All time-based notifications derive fire-times from the scheduler reading the Panchang cache.**

---

## 16. Module 14: Content Management System

**Priority:** 🟡 HIGH
**Complexity:** Medium

### 16.1 Content Lifecycle
States: Draft → In Review → Published → (Archived)
- Only Published content reaches the API
- Every change versioned with author, timestamp, review state
- Source attribution on each item
- AI assistant only grounds in Published content
- Regional relevance tags gate display
- Flag-and-review correction workflow

### 16.2 Content Types
- Festival descriptions, puja methods, katha
- Educational content (Panchang basics, Tithi, Nakshatra explanations)
- Mantras, translations
- Calendar templates
- Marketplace content (service taxonomy, product categories)

---

## 17. Module 15: Admin Panel

**Priority:** 🟡 HIGH
**Complexity:** Medium-High

### 17.1 Content Management
- Festival, vrat, educational content CRUD
- Image upload, translations, regional relevance
- Scheduling, review of AI-generated explanations
- Template design

### 17.2 Marketplace Administration
- **Pandit approval queue** — verify credentials, approve/reject
- **Seller approval queue** — KYC review, approve/reject
- Service/product taxonomy management
- Commission & fee configuration
- Booking/order/dispute consoles
- Payout management & reconciliation

### 17.3 Reporting
- Signups, DAU/MAU, subscription conversions
- Calendar downloads, most-viewed festivals
- Reminder usage, regional distribution
- Revenue (subscriptions + marketplace)
- Marketplace: booking volume, GMV, payout health

### 17.4 Access Control
- Role-based with audit trail on every content/config change
- Admin sub-roles: Content, Marketplace Ops, Finance, Superuser

---

## 18. Module 16: Pandit Services Marketplace

**Priority:** 🟢 MEDIUM (Phase 3)
**Complexity:** Very High

### 18.1 Overview
Two-sided service marketplace: verified pandits offer ceremonial services; paid subscribers book and pay. Platform owns discovery, scheduling, payment (escrow), communication, reviews, and disputes.

### 18.2 Pandit (Provider) Side

#### 18.2.1 Registration & Onboarding
1. Create provider account (reuses existing auth; one login can be patron + pandit)
2. Accept Partner Agreement, code of conduct, cancellation policy
3. Complete profile and service catalogue
4. Complete identity/credential verification (KYC)
5. Connect payout account (Stripe Connect)
6. Submit for review → operations approves

**Hard gate:** Profile never publicly listed until verification passes AND operations approves.

#### 18.2.2 Identity & Credential Verification
- Government ID (KYC provider: Stripe Identity/Onfido/Persona)
- Background check (where legally available: US/UK)
- Credential/lineage attestation (self-declared vs platform-verified)
- Address verification
- Re-verification on periodic cadence and trigger events

#### 18.2.3 Service Catalogue
Each offering is a `PanditService` linked to a platform-managed `ServiceType`:
- **Festival officiation** — linked to v2.0 festival identifiers
- **Pujas & ceremonies** — aligned to muhurat event types
- **Astrology/consultation** (optional)

Per service: mode(s), duration, inclusions, languages, price.

#### 18.2.4 Service Modes & Travel
| Setting | Description |
|---------|-------------|
| In-person — will travel | Max 100-mile radius from base |
| Travel fee | Flat, per-mile, or banded |
| Requires pickup | Patron arranges transport |
| Live-remote | 1:1 video, no geographic limit |

#### 18.2.5 Pricing & Samagri
- Base price (dakshina/fee) per service
- Travel fee (in-person only)
- Samagri option (pandit brings for extra charge, or patron self-arranges via §7.3/Marketplace B)
- Platform service fee & taxes
- All quotes itemized

#### 18.2.6 Availability & Calendar
- Working hours, days off, blackout dates, minimum lead time
- Capacity rules (one ceremony per slot, buffer/travel time)
- Conflict prevention (no double-booking)
- Auto vs manual acceptance mode
- Optional Google/Apple Calendar sync

### 18.3 Patron (Customer) Side

#### 18.3.1 Discovery & Search
Filter by: service/ceremony, festival, mode, date/time (muhurat-aware), location/distance, language, tradition, price, rating, verification badges.
Sort by: recommended, rating, price, distance, soonest availability.

#### 18.3.2 Booking Flow
1. Select service and mode
2. Pick date & time (muhurat finder integration)
3. In-person: enter address, validate travel radius, compute travel fee
4. Choose samagri option
5. Add notes/special requests
6. Review itemized quote → pay

Advance booking: up to 60 days; minimum: pandit's lead time.

#### 18.3.3 Post-Service
- Rate and review (verified-booking only)
- Rebook/favourite a pandit
- Recurring booking for annual family pujas

### 18.4 Booking Lifecycle

| State | Money |
|-------|-------|
| Requested | Payment authorized (held) |
| Confirmed | Captured into escrow |
| Reschedule pending | Held |
| In progress | Held |
| Completed | Payout scheduled (minus commission) |
| Cancelled — patron | Refund per policy |
| Cancelled — pandit | Full refund; pandit penalty |
| No-show | Resolved per no-show rules |
| Disputed | Payout frozen |
| Refunded/Closed | Terminal |

### 18.5 Payments & Escrow
- **Stripe Connect** (Express/Custom accounts)
- Hold → release after completion + holdback window
- Configurable commission take-rate
- Automated payout schedule with on-demand option

### 18.6 Cancellation Policy (Reference: 30-Day Window)
| When Patron Cancels | Refund |
|---------------------|--------|
| 30+ days before | Full refund |
| Inside 30 days | Partial (e.g., 50%) |
| Very close/on the day or no-show | No refund |

Policy snapshot stored on each booking.

### 18.7 Reviews, Ratings & Ranking
- Two-way reviews (patron ↔ pandit)
- Verified-booking only
- Moderation with content rules
- Recommendation ranking: rating, completion rate, response time, proximity, price — with anti-gaming

### 18.8 Messaging & Live Video
- Per-booking chat (text + images), PII masking
- Pre-booking Q&A (rate-limited)
- Live 1:1 video for remote ceremonies (Agora/Twilio/LiveKit)
- Session logs for completion/no-show resolution

### 18.9 Trust & Safety
- Verification gate, address privacy (revealed only after confirmed+paid booking)
- Emergency/SOS during home visits
- Dispute resolution workflow with evidence
- Fraud detection (duplicate accounts, fake reviews, off-platform leakage)
- Provider standing score (completion rate, cancellation rate, response time, rating)

> **🔴 PM Critique — Missing Features:**
> 1. **Group/Multi-Pandit Bookings** — weddings need multiple pandits; this should be Phase 2 marketplace
> 2. **Gift a Puja** — allow users to gift a ceremony booking to family members
> 3. **Pandit Comparison View** — side-by-side comparison of 2-3 pandits

> **🔵 Architect Critique:** The live video component is the highest-risk integration. Recommend starting with in-person only for Marketplace MVP; add live-remote in Phase 2. Also: the messaging system should use WebSocket with message persistence, not polling.

---

## 19. Module 17: Pooja Items Marketplace

**Priority:** 🟢 MEDIUM (Phase 3)
**Complexity:** High

### 19.1 Overview
Multi-vendor shop for physical pooja/festival items. Headless Shopify store for commerce backbone; Stripe Connect for seller payouts (shared with Pandit Marketplace).

### 19.2 Architecture
| Responsibility | Owner |
|---------------|-------|
| Catalogue, variants, bundles, inventory | Shopify |
| Cart, checkout, payment, PCI | Shopify |
| Sales tax/VAT | Shopify Tax |
| Shipping rates, tracking | Shopify |
| Seller onboarding, KYC, approval | The Pandit |
| Commission & seller payouts | The Pandit (Stripe Connect) |
| Subscription gating | The Pandit |
| Reviews, disputes, returns | The Pandit |

### 19.3 Product Model
| Type | Description | Example |
|------|-------------|---------|
| By weight | Weight variants with price/stock each | Ghee 250g/500g/1kg |
| By count/pack | Pack-size variants | Diyas — pack of 11/21/51 |
| Bundle/kit | Composed product at kit price | Diwali Lakshmi Puja Kit |
| Festival bundle | Auto-suggested from festival's items list | Navratri Samagri Set |

### 19.4 Seller Requirements
- Apply, pass KYC, connect Stripe Connect payout
- List products (weight/count/bundles) through seller portal
- Manage inventory, pricing, shipping
- Mark orders dispatched with carrier + tracking (written back to Shopify)
- View earnings, payouts, reviews

### 19.5 Buyer Requirements
- Browse open to all; checkout requires Silver/Gold subscription
- Multi-seller cart (split per seller for fulfillment/payout, single checkout)
- Track orders, request returns, review products

### 19.6 Integration Points
- **§7.3 Puja Samagri Checklist →** each item buyable; "buy the kit" adds bundle to cart
- **§5.5.3 Festival Pages →** required-items list offered as festival bundle
- **Pandit Booking →** offer samagri kit when pandit doesn't bring samagri
- **§7.2 Festival Prep →** "order your samagri now" prompts ahead of festivals

### 19.7 Commission & Payouts
- Configurable rate (default ~12.5%, admin-editable, 10–15% band)
- On item subtotal only; shipping passed through
- Payout after delivery + holdback window via Stripe Connect

> **🔴 PM Critique:** The Shopify dependency is a significant vendor lock-in risk. Consider abstracting the commerce layer behind an interface so it could be swapped for a self-hosted solution (Medusa.js, Saleor) if costs become prohibitive at scale.

> **🟢 Developer Critique:** Headless Shopify + Stripe Connect is a pragmatic choice that avoids building commerce from scratch. However, the multi-vendor model in Shopify (single-store, vendors as metafields) has limitations at scale. Need to carefully design the webhook→payout pipeline for reliability and reconciliation.

---

## 20. Module 18: Sharing, Export & Integration

**Priority:** 🟡 HIGH
**Complexity:** Medium

### 20.1 Share Destinations
WhatsApp, SMS, email, Facebook, Instagram Stories, Telegram.

### 20.2 Export Formats
PDF, PNG, iCal, Google/Apple/Outlook calendars.

### 20.3 Shareable Content
Daily Panchang, festival details, muhurat details, calendar images, permitted notes, vrat reminders.

---

## 21. Module 19: Widgets & Quick Access

**Priority:** 🟢 MEDIUM
**Complexity:** Medium

### Mobile Widgets
- Today's Tithi/Nakshatra, sunrise/sunset
- Next festival, Rahu Kalam alert
- Moon phase, daily mantra, festival countdown

### Premium Lock-Screen Widgets
- Today's Panchang, festival countdown, vrat reminders

### Web Dashboard
- Today's Panchang, month calendar, upcoming festivals
- Notes, bookmarks, printable-calendar generator, subscription management

---

## 22. Module 20: Advanced Features

**Priority:** 🟢 MEDIUM to LOW
**Complexity:** Varies

| Feature | Priority | Phase |
|---------|----------|-------|
| Festival Preparation Mode | Medium | 2 |
| Puja Samagri Checklist | Medium | 2 |
| Sankalp Journal | Low | 3 |
| Mantra & Japa Tracker | Low | 3 |
| Temple & Community Calendar | Low | 3 |
| Children's Learning Mode | Low | 3 |
| Pilgrimage Planner | Low | 3 |
| Daily Dharma Card | Medium | 2 |
| Smart Hindu Event Creation | Medium | 2 |

---

## 23. Non-Functional Requirements

| Concern | Requirement |
|---------|-------------|
| Daily Panchang Load | ≤2s on normal connection, from cache |
| Availability (read path) | 99.9% monthly on Panchang & calendar |
| Festival-spike scaling | Auto-scale reads; pre-warm caches |
| Async work | PDF generation & reminder fan-out queue-driven |
| Offline | Current month, recent days, downloaded calendars |
| API contract | Versioned REST/JSON; backward-compatible within major version |
| Observability | Structured logging, request tracing, SLOs, alerting |
| Marketplace search | ≤1s typical for pandit/product search |
| Booking integrity | No double-booking; atomic payment+slot reservation |
| Payment reliability | Idempotent, retried, reconciled; webhook-driven |
| Video quality | Adaptive bitrate; audio-only fallback |
| Scale planning | Design for global diaspora; documented DAU/MAU growth assumptions |

---

## 24. Security & Privacy

### 24.1 Sensitive Data Vault
- Birth date/time/place, family birth details → separate encrypted vault
- Access-logged, excluded from analytics
- Pandit verification documents, background-check refs → Vault
- Patron ceremony addresses → Vault (revealed only for confirmed bookings)
- Seller KYC documents → Vault

### 24.2 Authentication & Authorization
- OAuth/OIDC for Google & Apple; secure token storage; refresh-token rotation
- Role-based admin access with audit trail
- API rate limiting at gateway
- TLS everywhere; secrets in managed secret store

### 24.3 Privacy Controls
- Account deletion, data export (GDPR + UAE)
- Delete notes, family members
- Disable location, manage notification permissions
- Control AI data usage
- Data residency: reconcile GDPR (EU) and UAE per governing region

### 24.4 Payment Security
- PCI via Stripe/Shopify (no raw card data on platform)
- SCA/3-DS where required
- Idempotent payment operations

### 24.5 Marketplace Trust
- PII masking in messaging
- Off-platform circumvention detection
- Contact-info masking
- In-person safety: SOS/support affordance

---

## 25. Subscription Tier Feature Matrix

| Feature | Basic (Free) | Silver | Gold |
|---------|:---:|:---:|:---:|
| Daily Panchang | ✅ | ✅ | ✅ |
| Day/Month View | ✅ (basic) | ✅ (full) | ✅ (full) |
| Week/Year View | ❌ | ✅ | ✅ |
| Notes/Bookmarks/Reminders | 5 each | Unlimited | Unlimited |
| Tithi-based Recurring Reminders | ❌ | ✅ | ✅ |
| Regional Festival Customization | ❌ | ✅ | ✅ |
| Saved Locations | 1 | 3 | Unlimited |
| Family Members | ❌ | 5 | Unlimited |
| Calendar Export | Limited | 12-month PDF | 12-15 month HD 300 DPI |
| Muhurat Finder | ❌ | Basic | Advanced + AI |
| AI Assistant | ❌ | Limited | Full |
| Hindu Life Planner | ❌ | ❌ | ✅ |
| Vrat Tracker/Completion | ❌ | ✅ | ✅ |
| Widgets | ❌ | ✅ | ✅ + Lock-screen |
| Calendar Sync | ❌ | ✅ | ✅ |
| Book a Pandit | Browse only | ✅ | ✅ + reduced fee |
| Pooja Items Shop | Browse only | ✅ | ✅ |
| Ads | Yes | No | No |

---

## 26. Data Model

### 26.1 Core Entities (Consolidated)

| Entity | Key Fields | Notes |
|--------|-----------|-------|
| User | id, auth refs, display name, prefs, tier, roles[] | Composite roles |
| SensitiveVault | userId, DOB, TOB, POB, family birth data, pandit KYC, seller KYC, addresses | Encrypted, access-logged |
| Location | id, label, lat, lon, tz, dst rule | Drives all computation |
| PanchangDay (cache) | date, locationKey, ayanamsa, scheme, all angas+times | Precomputed |
| FestivalRule | id, name, anga rule, scheme, region tags, priority | Rules, not dates |
| FestivalOccurrence | festivalRuleId, date, locationKey, year | Derived cache |
| FestivalContent | festivalId, locale, body, puja, katha, samagri | CMS-versioned |
| Reminder | id, userId, recurrence spec, nextFireTime, locationKey | Multi-type recurrence |
| Note / Bookmark | id, userId, dateRef, category, body | Greg or Tithi ref |
| FamilyMember | id, userId, relation, birth Tithi/Nakshatra | Birth → Vault |
| VratRecord | id, userId, vratId, status, sankalp, notes | Status tracking |
| CalendarJob | id, userId, template, range, status, outputUrl | Async PDF |
| Subscription | userId, tier, source, status, expiry | Apple/Google/Stripe |
| ContentVersion | entityId, version, author, reviewState, source | Editorial provenance |
| **Pandit** | id, userId, bio, baseLocationId, languages, tradition, verification, rating, payout | Marketplace A |
| **PanditService** | id, panditId, serviceTypeId, modes, duration, price, samagri | Marketplace A |
| **ServiceType** | id, category, name, festivalRef?, taxonomy | Admin-curated |
| **Booking** | id, patronId, panditId, serviceId, mode, time, status, priceBreakdown, policy | Marketplace A |
| **BookingEvent** | bookingId, fromState, toState, actor, timestamp | Audit trail |
| **Payment** | id, bookingId, stripeRefs, amount, commission, status | Escrow |
| **Payout** | id, recipientId, amount, period, status | Shared A+B |
| **Review** | id, subjectId, authorId, authorRole, stars, body, type | Two-way, verified |
| **Conversation / Message** | id, bookingId?, participants, body, flags | PII masked |
| **VideoSession** | bookingId, provider, joinLog, recordingRef? | Live remote |
| **Dispute** | id, bookingId/orderId, raisedBy, state, resolution | Payout freeze |
| **Seller** | id, userId, shopName, kycStatus, payoutRef, standing | Marketplace B |
| **ProductRef** | id, shopifyProductId, sellerId, category, type | Shopify overlay |
| **OrderRef** | id, shopifyOrderId, buyerId, status, totals | Shopify mirror |
| **OrderSellerSplit** | orderRef, sellerId, items, commission, payoutStatus | Per-seller split |
| **Fulfillment** | orderSellerSplit, carrier, tracking, shippedAt | Written to Shopify |
| **ReturnRequest** | id, orderRef, items, reason, state, refund | Returns |
| **ProductReview** | id, productRef, buyerId, stars, body | Verified purchase |

---

## 27. Expert Critique & Recommendations

### 🔴 Sr Product Manager Perspective

#### Strengths
1. **Exceptional breadth** — the spec covers an end-to-end Hindu lifestyle ecosystem
2. **Strong differentiators** — Tithi-based reminders, festival rule engine, and marketplace integration are genuine competitive advantages
3. **Smart monetization** — three-tier subscription + marketplace commissions + calendar sales creates multiple revenue streams
4. **Good user journey mapping** — new user, daily user, and premium user journeys are well-thought-out

#### Critical Gaps & Recommendations
| # | Gap | Impact | Recommendation | Priority |
|---|-----|--------|----------------|----------|
| 1 | **No onboarding flow specification** | High churn risk for new users | Define a 3-5 screen onboarding wizard: location → calendar preference → interests → first reminder → account creation | P0 |
| 2 | **No retention/engagement strategy** | Users may forget the app exists | Add daily streaks, spiritual goals gamification, "Panchang of the Day" push notification strategy | P1 |
| 3 | **Missing analytics/A-B testing framework** | Can't optimize conversion | Spec an experimentation framework for subscription conversion optimization | P1 |
| 4 | **No social/community features** | Missed engagement opportunity | Consider a community feed for festival experiences, temple visits (Phase 3) | P2 |
| 5 | **Temple Administrator persona missing** | Limits B2B revenue | Add temple admin features for managing events, calendars, and bulk supplies | P2 |
| 6 | **Family sharing permissions undefined** | Conflict risk | Define invitation flow, admin vs member roles, edit conflict resolution | P1 |
| 7 | **Marketplace cold-start strategy underspecified** | Chicken-and-egg problem | Define seed pandit/seller acquisition plan, incentive structure, geographic launch sequence | P0 |
| 8 | **No competitive analysis section** | Market positioning unclear | Document top 5 competitors (Drik Panchang, AstroSage, Hindu Calendar) and feature gap analysis | P1 |

### 🔵 Sr Enterprise Architect Perspective

#### Strengths
1. **Clean service decomposition** — each domain has clear boundaries
2. **Cache-first strategy** is correct for this workload
3. **Sensitive data vault** separation is architecturally sound
4. **Single payout engine** across both marketplaces avoids duplication

#### Critical Gaps & Recommendations
| # | Gap | Impact | Recommendation | Priority |
|---|-----|--------|----------------|----------|
| 1 | **No API versioning strategy defined** | Breaking changes in production | Define URL-based versioning (/v1/, /v2/) with deprecation policy and migration guides | P0 |
| 2 | **Event-driven architecture not specified** | Tight coupling between services | Introduce an event bus (AWS EventBridge / Kafka) for booking state changes, payout triggers, notification fan-out | P0 |
| 3 | **Location grid granularity undefined** | Cache efficiency vs accuracy trade-off | Define 0.1° lat/lon (~11km) as configurable default | P0 |
| 4 | **Multi-tenancy for content not addressed** | Regional content isolation | Design content partitioning by region/locale with fallback chains | P1 |
| 5 | **Disaster recovery / backup strategy missing** | Data loss risk | Define RPO/RTO targets, backup cadence, failover strategy | P0 |
| 6 | **CDN strategy for static content undefined** | Performance in global diaspora | Specify CDN for cached Panchang responses, calendar images, CMS content | P1 |
| 7 | **Rate limiting strategy needs detail** | Abuse prevention | Define per-endpoint, per-tier rate limits with graceful degradation | P1 |
| 8 | **Database migration strategy absent** | Schema evolution risk | Plan for schema versioning, zero-downtime migrations, data backfill | P1 |

### 🟢 Lead Developer Perspective

#### Strengths
1. **Swiss Ephemeris choice is validated** — well-supported, accurate, clear licensing path
2. **Precompute-and-cache is the right call** — avoids client complexity
3. **Headless Shopify for e-commerce** avoids building payments/PCI from scratch
4. **Async PDF generation** prevents blocking the main app

#### Critical Gaps & Recommendations
| # | Gap | Impact | Recommendation | Priority |
|---|-----|--------|----------------|----------|
| 1 | **Swiss Ephemeris binding strategy undefined** | Build risk | Use `pyswisseph` (Python C-extension) for the computation service; validate edge cases early | P0 |
| 2 | **Testing strategy for astronomical calculations** | Accuracy is the #1 brand promise | Build reference dataset from Drik Panchang/established sources for 100+ dates × 10+ locations; automate in CI | P0 |
| 3 | **Offline sync strategy undefined** | Data conflicts on reconnection | Define conflict resolution: server-wins for Panchang cache, last-write-wins for notes with version vectors | P1 |
| 4 | **Mobile push notification architecture** | Delivery reliability | Use a fan-out service (SNS → APNs/FCM) with delivery tracking and retry logic | P1 |
| 5 | **No error handling specification** | Poor user experience on failures | Define error taxonomy, user-facing messages, retry policies, circuit breakers | P1 |
| 6 | **Calendar rendering performance** | Month view with many overlays could be slow | Use virtualized rendering for calendar grids; lazy-load festival details | P1 |
| 7 | **Video SDK evaluation not done** | Cost and reliability risk | Evaluate Agora vs Twilio vs LiveKit on: cost per minute, global latency, recording, mobile SDK quality | P1 |
| 8 | **Shopify webhook reliability** | Missed orders/payouts | Implement webhook verification, idempotency keys, dead-letter queue, and reconciliation cron | P0 |

---

*End of Consolidated Requirements Document v3.0*
