# Virtual Learning Environment Proposal — Open Source Stack

## The scenario

- 200 international delegates, 3 days
- ~10 instructors, each offering a 2-hour session per day (up to 30 sessions total)
- Global timezones with overlapping schedules
- Delegates choose sessions; personal schedules tracked
- Replace Zoom with open-source conferencing
- Extensible: your own tools should be linkable in

---

## Summary: one possible open-source stack

| Function | Recommended tool |
|---|---|
| Video conferencing (replacing Zoom) | **BigBlueButton** |
| LMS / course delivery / completion | **Moodle** |
| Registration & event management | **Indico** (CERN) |
| Authentication / SSO | **Keycloak** |
| Organiser messaging + public lists | **Matrix / Element** |
| Course materials storage | **Nextcloud** |

Everything above uses open, standard protocols (OAuth2 / OIDC, LTI, OAI-PMH, SMTP) that allow your own tools to connect.

---

## Component by component

### 1. Video conferencing — replacing Zoom

**[BigBlueButton](https://bigbluebutton.org/)** (LGPL)

The leading open-source virtual classroom platform, purpose-built for education (not repurposed meetings software). Key features:

- Breakout rooms, shared whiteboards, polls, shared notes, screen sharing, raise-hand queue
- Session recording with full playback
- Natively integrated into Moodle 4.0+ (built-in, no extra plugin needed)
- Supports 100–300 concurrent participants per room (scales with server capacity)
- LTI standard lets other tools launch rooms
- Localised into 65+ languages — suitable for international delegates
- Version 3.0 (2025) added plugin architecture and built-in quiz → learning analytics

**[Jitsi Meet](https://jitsi.org/)** (Apache 2.0) is a simpler, lower-resource alternative if BigBlueButton feels heavy,
but has fewer education-specific features and weaker LMS integration.

---

### 2. LMS — course materials, scheduling, completion tracking

**[Moodle](https://moodle.org/)** (GPL)

The world's most-used open-source LMS. Covers most requirements directly:

| Requirement | Moodle feature |
|---|---|
| Course material manager | Resources (Pages, Files, Books, Videos), organised per course/session |
| Organiser messaging to delegates | Built-in Messaging + News Forum (all delegates subscribed by default) |
| Public message lists / discussion | Forums (per course, site-wide announcements) |
| Personal schedules | Calendar (auto-populates from enrolled sessions) |
| Completion recording | Completion Tracking — auto-marks when delegate views, submits, or attends; report available to organisers |
| Room management | BBB activity links per session; opens the right room at the right time |
| Course selection / self-enrolment | Self-enrolment keys per course; or enrolment via registration import |

Moodle can be extended with ~2,000 plugins. Your own tools can integrate via REST API, LTI, or database.

---

### 3. Registration and delegate management

**[Indico](https://getindico.io/)** (MIT, developed at CERN)

Used by CERN (900,000+ events), the United Nations, and 200+ other institutions. Directly matches the scenario:

- Flexible registration forms (country, session preferences, etc.)
- Timetable manager with drag-and-drop scheduling across 3 days
- Supports multiple parallel tracks / sessions at different times
- Delegate badge generation and check-in
- Abstract / session submission if instructors propose content
- Payment integration if registration is paid
- REST API for exporting delegate lists to Moodle or Keycloak

**[Pretix](https://pretix.eu/)** (AGPL) is a good alternative if registration is the focus and event management
is simpler — it excels at ticketing, check-in, and payments but has less scheduling depth.

---

### 4. Authentication and security

**[Keycloak](https://www.keycloak.org/)** (Apache 2.0, donated to CNCF)

Provides single sign-on (SSO) across all components:

- One login for Indico, Moodle, BigBlueButton, Nextcloud, Matrix
- Protocols: OpenID Connect, OAuth 2.0, SAML 2.0
- Multi-factor authentication (TOTP, WebAuthn)
- Social login (Google, GitHub, institution accounts) if desired
- User federation from LDAP / Active Directory if you have an existing directory
- Self-registration flows with email verification
- Fine-grained role management (delegate, instructor, organiser, admin)

Moodle integrates with Keycloak via OAuth2 (built-in). BigBlueButton uses Moodle for auth.
Indico supports OAuth/SAML. Nextcloud has an OIDC app.

---

### 5. Organiser messaging and public message lists

**[Matrix](https://matrix.org/) / [Element](https://element.io/)** (Apache 2.0)

A decentralised, federated messaging protocol — think "email, but for chat":

- **Organiser → delegates**: broadcast rooms (read-only or moderated)
- **Public discussion lists**: open rooms per session/topic, persistent history
- **Private delegate messaging**: direct messages between participants
- **Bridging**: can bridge to Slack, Teams, Discord if some participants prefer those
- End-to-end encrypted option
- Embeds into web pages via the Element widget API
- Can be linked from Moodle course pages

A lighter-weight alternative is **[Mattermost](https://mattermost.com/)** (MIT), which is closer to Slack
in UX and simpler to self-host.

---

### 6. Course material storage and sharing

**[Nextcloud](https://nextcloud.com/)** (AGPL)

- File store for slides, PDFs, videos, data sets
- Shareable links for instructors to upload materials before sessions
- Integrates with Moodle (repository plugin), Matrix, and Keycloak (OIDC)
- Collaborative document editing (Nextcloud Office / OnlyOffice)

---

## How the components connect

```
Delegate browser
    │
    ├─ Registration (Indico) ──→ exports delegate list ──→ Keycloak user accounts
    │
    ├─ Single login (Keycloak / SSO) ──→ token valid across all systems
    │
    ├─ LMS (Moodle)
    │       ├─ Course pages → materials from Nextcloud
    │       ├─ BigBlueButton activity → launches live session room
    │       ├─ Calendar → personal schedule auto-populated
    │       ├─ Completion tracking → auto-records attendance/view
    │       └─ News Forum / Messaging → organiser announcements
    │
    ├─ Live session (BigBlueButton) ← launched from Moodle
    │
    └─ Chat / discussion (Matrix/Element) ← embedded or separate tab
```

Your own tools can plug in anywhere via:
- Moodle REST API
- BigBlueButton API
- Keycloak token validation
- Nextcloud WebDAV / API
- Indico REST API

---

## What is not covered out of the box

| Gap | Notes |
|---|---|
| Automatic timezone detection and display | Moodle shows times in user's local timezone if users set it; Indico also supports per-user timezone |
| Intelligent session scheduling assistant | No off-the-shelf open-source tool; could be built on top of Indico's API |
| Certificate generation | Moodle has a certificate plugin; Indico can print badges |
| Live language interpretation | Not built into BigBlueButton; specialist tools (Interprefy etc.) are mostly proprietary |

---

## Approximate complexity / effort

| Component | Self-hosting difficulty |
|---|---|
| Moodle | Moderate — well-documented, Docker available |
| BigBlueButton | Higher — needs a dedicated server with good bandwidth |
| Keycloak | Moderate — Docker image; configuration is complex |
| Indico | Moderate — CERN provides Docker/Helm charts |
| Matrix/Element | Moderate — Synapse (server) + Element (client) |
| Nextcloud | Low — Docker, widely deployed |

---

## Recommendation

For 200 international delegates, 10 instructors, 3 days, session selection, and global timezones,
the **Moodle + BigBlueButton + Indico + Keycloak** stack covers essentially all stated requirements
with mature, well-supported open-source software. Matrix/Element can replace any Slack-style
messaging used alongside Zoom. None of it requires Zoom.

A realistic first step: **Moodle + BigBlueButton** (the most tightly coupled pair), with Keycloak
added for SSO once the core works, and Indico for the registration side.
