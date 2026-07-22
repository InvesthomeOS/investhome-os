import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const head = (title) => `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>${title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="_shared.css" />
</head>
<body>
`;

const foot = (prev, next) => `
  <div class="nav-pager">
    <a href="${prev.href}">← ${prev.label}</a>
    <a href="index.html">Review index</a>
    <a href="${next.href}">${next.label} →</a>
  </div>
</div>
</body>
</html>
`;

const topline = (statusBadge) => `
<div class="wrap">
  <nav class="crumb">
    <a href="index.html">UXR1 Review Package</a>
    <span>/</span>
    <span>Visual review · no code</span>
  </nav>
  <div class="topline">
    <div class="brand">
      <div class="brand-mark">IH</div>
      <div>
        <div class="brand-name">INVESTHOME OS</div>
        <div class="brand-sub">UXR1 Simplification · Visual deliverables only</div>
      </div>
    </div>
    <div class="badge-row">
      ${statusBadge}
      <span class="badge gate">NO IMPLEMENTATION</span>
    </div>
  </div>
`;

function screenPage(s) {
  const status =
    s.status === "approved"
      ? `<span class="badge ok">APPROVED</span>`
      : s.status === "conditional"
        ? `<span class="badge warn">CONDITIONAL</span>`
        : `<span class="badge pending">PENDING REVIEW</span>`;

  return (
    head(`UXR1 · Section ${s.num} — ${s.title} · INVESTHOME OS`) +
    topline(status) +
    `
  <header class="hero">
    <div class="eyebrow">Section ${s.num} · Wireframe + mockup</div>
    <h1>${s.title}</h1>
    <p class="lede">${s.lede}</p>
    <div class="meta-row">
      <span><strong>Route</strong> <code>${s.route}</code></span>
      <span><strong>Audience</strong> ${s.audience}</span>
      <span><strong>Primary UI</strong> ${s.primaryUi}</span>
    </div>
    <nav class="toc">
      <a href="#today">Today's work</a>
      <a href="#wireframe">Low-fi wireframe</a>
      <a href="#hifi">High-fidelity</a>
      <a href="#desktop">Desktop</a>
      <a href="#mobile">Mobile</a>
      <a href="#journey">Journey</a>
      <a href="#actions">Actions</a>
      <a href="#fields">Fields</a>
      <a href="#rationale">Rationale</a>
    </nav>
  </header>

  <section id="today">
    <div class="section-head">
      <h2>Today's work</h2>
      <span class="section-note">Who finishes faster · operational, not decorative</span>
    </div>
    <div class="today-work">
      <div class="today-work-grid">
        ${s.todayWork
          .map(
            (r) => `
        <div class="today-card">
          <div class="today-role">${r.role}</div>
          <div class="today-task">${r.task}</div>
          <div class="today-faster">${r.faster}</div>
        </div>`
          )
          .join("")}
      </div>
      <p class="today-principle">${s.todayPrinciple}</p>
    </div>
  </section>

  <section id="wireframe">
    <div class="section-head">
      <h2>Low-fidelity wireframe</h2>
      <span class="section-note">Structured layout · boxes only</span>
    </div>
    <p class="section-intro">${s.wireIntro}</p>
    <div class="wire">${s.wireHtml}</div>
  </section>

  <section id="hifi">
    <div class="section-head">
      <h2>High-fidelity mockup</h2>
      <span class="section-note">Premium light SaaS · sales/marketing friendly</span>
    </div>
    <p class="section-intro">${s.hifiIntro}</p>
    <div class="panel">
      <div class="panel-head">
        <span class="panel-title">Desktop frame · ${s.title}</span>
        <span class="badge pending">Mockup</span>
      </div>
      ${
        s.mockup
          ? `<img class="mock-img" src="${s.mockup}" alt="${s.title} high-fidelity desktop mockup" />
      <div class="mock-caption">${s.mockCaption}</div>`
          : s.hifiHtml
      }
    </div>
  </section>

  <section id="desktop">
    <div class="section-head">
      <h2>Desktop layout</h2>
      <span class="section-note">Primary working surface</span>
    </div>
    <div class="split">
      <div class="card">
        <h3>Composition</h3>
        <ul>${s.desktop.map((x) => `<li>${x}</li>`).join("")}</ul>
      </div>
      <div class="card">
        <h3>Density & hierarchy</h3>
        <ul>${s.density.map((x) => `<li>${x}</li>`).join("")}</ul>
      </div>
    </div>
  </section>

  <section id="mobile">
    <div class="section-head">
      <h2>Mobile behavior &amp; preview</h2>
      <span class="section-note">Phone-first adaptations · operational queue first</span>
    </div>
    <div class="split">
      <div class="mobile-preview">
        <div class="wire">${s.mobileWire}</div>
        <p class="mobile-note">Primary mobile job: finish today’s queue — not recreate the desktop dashboard.</p>
      </div>
      <div class="card">
        <h3>Behavior rules</h3>
        <ul>${s.mobile.map((x) => `<li>${x}</li>`).join("")}</ul>
      </div>
    </div>
  </section>

  <section id="journey">
    <div class="section-head">
      <h2>User journey</h2>
    </div>
    <div class="journey">
      ${s.journey
        .map(
          (step, i) =>
            (i ? `<span class="j-arrow">→</span>` : "") +
            `<span class="j-step">${step}</span>`
        )
        .join("")}
    </div>
    <p class="section-intro" style="margin-top:14px">${s.journeyNote}</p>
  </section>

  <section id="actions">
    <div class="section-head">
      <h2>Primary actions</h2>
    </div>
    <div class="panel">
      <table>
        <thead><tr><th>Action</th><th>Where</th><th>Outcome</th></tr></thead>
        <tbody>
          ${s.actions
            .map(
              ([a, w, o]) =>
                `<tr><td><strong>${a}</strong></td><td>${w}</td><td>${o}</td></tr>`
            )
            .join("")}
        </tbody>
      </table>
    </div>
  </section>

  <section id="fields">
    <div class="section-head">
      <h2>Visible &amp; hidden fields</h2>
      <span class="section-note">Progressive disclosure · docs 12–13</span>
    </div>
    <div class="field-grid">
      <div class="card field-box ok">
        <h3>Visible (daily)</h3>
        <ul>${s.visible.map((x) => `<li>${x}</li>`).join("")}</ul>
      </div>
      <div class="card field-box hide">
        <h3>Hidden (Details / Advanced)</h3>
        <ul>${s.hidden.map((x) => `<li>${x}</li>`).join("")}</ul>
      </div>
    </div>
  </section>

  <section id="rationale">
    <div class="section-head">
      <h2>Design rationale</h2>
      <span class="section-note">Why better than current</span>
    </div>
    <div class="callout">
      <h3>${s.rationaleTitle}</h3>
      <p>${s.rationale}</p>
    </div>
    <ul class="card" style="margin-top:12px;list-style:none">
      ${s.rationaleBullets.map((x) => `<li style="padding-left:14px;position:relative;font-size:14px;color:var(--ink-muted);margin:8px 0">${x}</li>`).join("")}
    </ul>
  </section>

  <div class="checkpoint">
    <div class="eyebrow">Approval gate</div>
    <h2>Section ${s.num} ready for review</h2>
    <p>Visual package only. No routes, components, or APIs changed. Approve or request changes before any implementation.</p>
    <div class="actions">
      <a class="btn" href="index.html">Back to package index</a>
      <a class="btn ghost" href="${s.nextHref}">Next: ${s.nextLabel}</a>
    </div>
  </div>
` +
    foot(s.prev, s.next)
  );
}

const screens = [
  {
    file: "04-dashboard.html",
    num: "04",
    title: "Dashboard",
    status: "pending",
    lede: "One calm command surface: today strip, sales funnel, unit availability, projects, marketing production, and follow-ups — without BI explorer noise.",
    route: "/dashboard",
    audience: "All authenticated staff",
    primaryUi: "Widget grid + drill-downs",
    todayWork: [
      { role: "Salesperson", task: "Clear overdue follow-ups before noon", faster: "Today strip + Follow-ups list open the person or deal in one tap — no BI tour." },
      { role: "Marketer", task: "Confirm this week’s content shipped", faster: "Marketing production widget drills to Content Studio, not a 30-item rail." },
      { role: "Investor manager", task: "See which deals need capital-path attention", faster: "Funnel + follow-ups surface stuck proposals without a separate investor app." },
      { role: "Executive", task: "Glance commercial health in 30 seconds", faster: "Funnel + availability + projects only — no decorative charts or platform widgets." },
    ],
    todayPrinciple: "Backend still powers reports and BI; the default Dashboard hides that complexity and routes people into today’s work.",
    wireIntro: "Sidebar uses the proposed primary nav. Content prioritizes personal today metrics, then commercial glance widgets with explicit empty states and drill targets.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>INVESTHOME OS</span><span>[Search] [+] [Avatar]</span></div>
        <div class="wire-body">
          <div class="wire-nav">
            <div class="item active">Dashboard</div>
            <div class="item">Customers</div>
            <div class="item">Sales</div>
            <div class="item">Inventory</div>
            <div class="item">Projects</div>
            <div class="item">Marketing</div>
            <div class="item">Content</div>
            <div class="item">Calendar</div>
            <div class="item">Tasks</div>
            <div class="item">Documents</div>
            <div class="item">Reports</div>
            <div class="item" style="opacity:.5">Finance</div>
            <div class="item" style="opacity:.5">AI</div>
          </div>
          <div class="wire-main">
            <div class="wire-label">Today · Tue 21 Jul</div>
            <div class="wire-row">
              <div class="wire-box"><div class="wire-label">New Leads</div><div class="wire-value">12 ↑3</div></div>
              <div class="wire-box"><div class="wire-label">Follow-Ups</div><div class="wire-value">8 overdue</div></div>
              <div class="wire-box"><div class="wire-label">Tasks due</div><div class="wire-value">5</div></div>
              <div class="wire-box"><div class="wire-label">Meetings</div><div class="wire-value">3 today</div></div>
            </div>
            <div class="wire-row">
              <div class="wire-box tall" style="flex:1.2">
                <div class="wire-label">Sales Funnel → Sales</div>
                <div class="wire-bars">
                  <div class="wire-bar" style="--w:90%"></div>
                  <div class="wire-bar" style="--w:70%"></div>
                  <div class="wire-bar" style="--w:50%"></div>
                  <div class="wire-bar" style="--w:35%"></div>
                </div>
              </div>
              <div class="wire-box tall">
                <div class="wire-label">Unit Availability (donut) → Inventory</div>
                <div style="margin-top:10px;text-align:center;font-size:11px">Available · Reserved · Sold</div>
              </div>
            </div>
            <div class="wire-row">
              <div class="wire-box tall"><div class="wire-label">Monthly Sales</div><div class="wire-bars"><div class="wire-bar" style="--w:40%"></div><div class="wire-bar" style="--w:65%"></div><div class="wire-bar" style="--w:80%"></div></div></div>
              <div class="wire-box tall"><div class="wire-label">Active Projects</div><div style="margin-top:6px">North Towers ████░ 72%<br/>Marina ██░░░ 41%</div></div>
            </div>
            <div class="wire-box muted"><div class="wire-label">Follow-ups</div>Ada Yılmaz — Proposal sent — due today — [Open]</div>
          </div>
        </div>
      </div>`,
    hifiIntro: "Light, spacious command center. FunnelChart + DonutChart are intentional UXR1 sales-UX exceptions.",
    mockup: "mockups/04-dashboard-desktop.png",
    mockCaption: "High-fidelity desktop mock · Today KPIs, sales funnel, unit availability donut, projects, marketing, calendar/tasks.",
    desktop: [
      "Fixed left nav (proposed IA) + sticky top chrome (search, quick add, avatar)",
      "Row 1: personal Today KPIs (leads, follow-ups, tasks, meetings)",
      "Row 2: Sales Funnel (FunnelChart) + Unit Availability (DonutChart)",
      "Row 3: Monthly Sales bars + Active Projects progress",
      "Row 4: Marketing production + Calendar + Tasks",
      "Footer list: Follow-ups with Open deep links",
    ],
    density: [
      "Wide whitespace; one job per widget",
      "Every chart declares source + drill target + empty CTA",
      "No BI explorer, activity feed, or dual rails on default",
      "Restricted Finance/AI sit below divider, role-gated",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Today · Clear queue</div>
        <div class="ph-body">
          <div class="wire-row">
            <div class="wire-box"><div class="wire-value">12</div><div class="wire-label">Leads</div></div>
            <div class="wire-box"><div class="wire-value">8</div><div class="wire-label">Follow-ups</div></div>
          </div>
          <div class="wire-box muted"><div class="wire-label">Do next</div>Ada Y. — Proposal — Call · Open</div>
          <div class="wire-box muted"><div class="wire-label">Do next</div>M. Kaya — Qualify — Open</div>
          <div class="wire-box"><div class="wire-label">Funnel chips</div>New 24 · Prop 11 · Hold 5</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab active">Home</div>
          <div class="ph-tab">Sales</div>
          <div class="ph-tab">Inv</div>
          <div class="ph-tab">More</div>
        </div>
      </div>`,
    mobile: [
      "Bottom tab: Home / Sales / Inventory / More",
      "Follow-ups queue is the primary scroll — not a chart wall",
      "KPI cards 2×2; funnel becomes horizontal stage chips + counts",
      "Donut collapses to status chips on narrow widths",
      "Every row opens person or deal in one tap",
    ],
    journey: ["Open OS", "Scan Today", "Drill funnel or follow-up", "Act in Sales / Tasks"],
    journeyNote: "Dashboard is a router to work — not a second BI product. Each widget has one drill destination.",
    actions: [
      ["Open follow-up", "Follow-ups list", "Customer or opportunity"],
      ["Drill Sales Funnel", "Funnel widget", "/dashboard/sales"],
      ["Drill Unit Availability", "Donut widget", "/dashboard/inventory"],
      ["Open project", "Active Projects", "/dashboard/projects/[id]"],
      ["Plan day", "Empty Today CTA", "Calendar / Tasks"],
    ],
    visible: [
      "New leads count · Follow-ups overdue/due",
      "Tasks due · Meetings today",
      "Funnel stage counts · Unit status mix",
      "Monthly closed sales · Project progress/health",
      "Marketing shipped this week · Next calendar/tasks",
    ],
    hidden: [
      "BI explorer dimensions / ad-hoc queries",
      "Platform / G15 admin widgets",
      "Dense finance P&L (Finance role)",
      "Automation run logs · AI prompt telemetry",
      "Full activity feed (optional later under Dashboard)",
    ],
    rationaleTitle: "One glance replaces three competing homes",
    rationale:
      "Current staff land in crowded rails and analytics surfaces that require training. The proposed Dashboard answers “what needs me today?” with sales-native visuals and honest empty states.",
    rationaleBullets: [
      "Removes dual CRM/Marketing chrome from the default path",
      "Documents chart exceptions (funnel + availability donut) instead of fighting sales UX",
      "Every widget contracts definition, time window, source, drill, empty",
    ],
    prev: { href: "03-navigation-ia.html", label: "03 Navigation" },
    next: { href: "05-customer-profile.html", label: "05 Customer Profile" },
    nextHref: "05-customer-profile.html",
    nextLabel: "Customer Profile",
  },
  {
    file: "05-customer-profile.html",
    num: "05",
    title: "Customer Profile",
    status: "pending",
    lede: "One person, one URL — Lead, Buyer, and Investor as badges on a unified profile with progressive disclosure.",
    route: "/dashboard/customers/[id]",
    audience: "Sales · CRM · Investor relations",
    primaryUi: "Header + tabs · Overview default",
    todayWork: [
      { role: "Salesperson", task: "Call / WhatsApp the next action due today", faster: "Next-action card + channel buttons sit above the form dump." },
      { role: "Marketer", task: "Hand off a hot lead with context intact", faster: "One URL keeps source, preferences, and timeline — no re-entry into CRM." },
      { role: "Investor manager", task: "Confirm KYC / ticket only when Investor badge applies", faster: "Compliance fields stay in Details until the capital path is real." },
      { role: "Executive", task: "Understand where this person is in the journey", faster: "Lifecycle badges + journey strip replace three module names." },
    ],
    todayPrinciple: "One person, one profile. Advanced identity, UTM, and accreditation stay expandable so daily sales work stays fast.",
    wireIntro: "Unifies lead detail, CRM contact, and investor record. Overview surfaces next action, active deal, and preference snapshot before deep fields.",
    wireHtml: `
      <div class="wire-frame" style="min-width:680px">
        <div class="wire-top"><span>← Customers / Ada Yılmaz</span><span></span></div>
        <div class="wire-main" style="padding:16px">
          <div class="wire-row" style="align-items:center">
            <div class="wire-box" style="flex:0;min-width:56px;height:56px;display:grid;place-items:center">AV</div>
            <div style="flex:1">
              <div class="wire-value">Ada Yılmaz <span class="wire-chip">Lead</span><span class="wire-chip">Buyer</span></div>
              <div style="margin-top:4px">+90 … · ada@… · Owner: Selim · Lifecycle: Proposal sent</div>
            </div>
          </div>
          <div class="wire-row" style="margin-top:8px">
            <span class="wire-chip">Call</span><span class="wire-chip">WhatsApp</span><span class="wire-chip">Email</span>
            <span class="wire-chip">Schedule</span><span class="wire-chip">Match units</span><span class="wire-chip">More ▾</span>
          </div>
          <div style="margin:12px 0;border-bottom:1.5px solid #9aa3b5;padding-bottom:6px">
            <strong>Overview</strong> · Journey · Opportunities · Matches · Docs · Activity · Details
          </div>
          <div class="wire-row">
            <div class="wire-box tall"><div class="wire-label">Next action</div>Follow up proposal<br/>Due Today 16:00<br/>[Done] [Snooze]</div>
            <div class="wire-box tall"><div class="wire-label">Active opportunity</div>North Towers A-1204<br/>Stage: Proposal<br/>[Open in Sales]</div>
            <div class="wire-box tall"><div class="wire-label">Preference snapshot</div>2+1 · 8–12M TRY<br/>Marina preferred<br/>[Edit]</div>
          </div>
          <div class="wire-box muted"><div class="wire-label">Timeline</div>• Today — Proposal PDF sent<br/>• Mon — Site visit<br/>• 12 Jun — Lead created</div>
        </div>
      </div>`,
    hifiIntro: "Premium CRM profile: identity first, actions second, tabs for depth — not a form dump.",
    mockup: "mockups/05-customer-profile-desktop.png",
    mockCaption: "High-fidelity desktop · Ada Yılmaz profile with Overview cards and journey tabs.",
    desktop: [
      "Breadcrumb + identity header (avatar, badges, contact, owner, lifecycle)",
      "Action bar: Call / WhatsApp / Email / Schedule / Match units / More",
      "Tabs: Overview (default), Journey, Opportunities, Matches, Docs, Activity, Details",
      "Overview: next action · active opportunity · preference snapshot · compact timeline",
      "Details accordion collapsed: identity, qualification, investor, UTM, compliance",
    ],
    density: [
      "One URL per person — badges reflect roles, not separate apps",
      "Create/edit: 5–8 daily fields; rest in Details",
      "Investor path adds fields without cloning the record",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Ada Yılmaz</div>
        <div class="ph-body">
          <div class="wire-box"><span class="wire-chip">Lead</span> Proposal sent</div>
          <div class="wire-row">
            <div class="wire-chip">Call</div><div class="wire-chip">WA</div><div class="wire-chip">Mail</div>
          </div>
          <div class="wire-box tall"><div class="wire-label">Next action</div>Follow up · Today</div>
          <div class="wire-box"><div class="wire-label">Active deal</div>A-1204 Proposal</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab active">Overview</div>
          <div class="ph-tab">Journey</div>
          <div class="ph-tab">More</div>
        </div>
      </div>`,
    mobile: [
      "Sticky identity + primary Call/WhatsApp",
      "Tabs become horizontal scroll chips",
      "Overview cards stack full-width",
      "Details accordion only — no long forms on mobile create",
    ],
    journey: ["Lead", "Qualified", "Opportunity", "Reserved", "Customer"],
    journeyNote: "Optional Investor badge branches from opportunity without a disconnected record. Convert to investor = add role + fields.",
    actions: [
      ["Call / WhatsApp / Email", "Action bar", "Opens channel with context"],
      ["Schedule", "Action bar", "Calendar event linked to person"],
      ["Match units", "Action bar", "Inventory match panel prefills prefs"],
      ["Done / Snooze follow-up", "Next action card", "Clears or postpones"],
      ["Open in Sales", "Active opportunity", "Pipeline drawer / board"],
    ],
    visible: [
      "Full name · phone · email · owner",
      "Lifecycle / status · source · next follow-up",
      "Active opportunity stage · preference snapshot (budget band, beds, project)",
      "Short notes · timeline highlights",
    ],
    hidden: [
      "Full address / geography",
      "UTM deep attribution · campaign internals",
      "Score breakdown · exact budget",
      "Secondary phones · LinkedIn · WhatsApp id",
      "KYC / accreditation (show when Investor)",
      "Investment ticket/risk prefs (Investor Details)",
    ],
    rationaleTitle: "Stop splitting one human across three apps",
    rationale:
      "Today lead, CRM, and investor UIs fragment history and force staff to relearn chrome. A unified profile with badges and progressive disclosure matches how sales actually work.",
    rationaleBullets: [
      "Journey strip is the mental model — not module names",
      "Matching and opportunities live on the same person",
      "Compliance/investor depth appear only when relevant",
    ],
    prev: { href: "04-dashboard.html", label: "04 Dashboard" },
    next: { href: "06-sales-pipeline.html", label: "06 Sales Pipeline" },
    nextHref: "06-sales-pipeline.html",
    nextLabel: "Sales Pipeline",
  },
  {
    file: "06-sales-pipeline.html",
    num: "06",
    title: "Sales Pipeline",
    status: "pending",
    lede: "Kanban-first pipeline with matching drawer — stages from New through Won/Lost, soft-hold urgency visible on cards.",
    route: "/dashboard/sales",
    audience: "Sales team · managers",
    primaryUi: "Kanban board · List secondary",
    todayWork: [
      { role: "Salesperson", task: "Move Ada from Proposal → Soft hold with a matched unit", faster: "Board + drawer match panel — no spreadsheet hop mid-deal." },
      { role: "Marketer", task: "See which Meta leads stall after handoff", faster: "Source on cards + overdue KPI show stall without a second pipeline." },
      { role: "Investor manager", task: "Track holds that need capital follow-up", faster: "Soft-hold column makes expiring urgency visible on the card." },
      { role: "Executive", task: "Know open / overdue / closing this week", faster: "KPI strip answers pipeline health; board is the workspace, not a report." },
    ],
    todayPrinciple: "Operational kanban first. List, attribution payloads, and finance settlement stay progressive — backend capable, UI calm.",
    wireIntro: "Board columns are the product. Card click opens a drawer; Match inventory is a visual panel, not a spreadsheet detour.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>Sales · [Board ●] [List] · Owner ▾ Project ▾</span><span>Open 86 · Overdue 8 · Holds 5</span></div>
        <div class="wire-main">
          <div class="wire-row" style="flex-wrap:nowrap;overflow:auto">
            ${["New|Ada Y. 8–12M Meta", "Qualified|M. Kaya Budget?", "Meeting|—", "Proposal|PDF sent", "Soft hold|Unit A12 expires"]
              .map(
                (c) => {
                  const [t, b] = c.split("|");
                  return `<div class="wire-box tall" style="min-width:110px;flex:0"><div class="wire-label">${t}</div><div class="wire-box muted" style="margin-top:6px">${b}</div></div>`;
                }
              )
              .join("")}
          </div>
          <div class="wire-box muted"><div class="wire-label">Drawer · Opportunity Ada Yılmaz</div>Stage Proposal → Change · Customer · Match 3 units · Follow-up Today</div>
        </div>
      </div>`,
    hifiIntro: "Spacious kanban with KPI strip and soft-hold emphasis — CRM that feels commercial, not enterprise-dense.",
    mockup: "mockups/06-sales-pipeline-desktop.png",
    mockCaption: "High-fidelity desktop · Sales board with stage columns and opportunity cards.",
    desktop: [
      "Header: Board/List toggle · Owner · Project filters · KPI strip",
      "Columns: New → Qualified → Meeting → Proposal → Soft hold → Reservation → Deposit → Contract → (Won/Lost via Closed filter)",
      "Cards: name, budget band, source, unit if held, follow-up cue",
      "Drawer: stage change, customer link, match panel, notes/docs",
    ],
    density: [
      "Won/Lost collapse into Closed filter on smaller widths",
      "Soft hold / Reservation / Deposit / Contract confirm before move",
      "Lost requires reason; Won requires closing checklist handoff",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Sales · Board</div>
        <div class="ph-body">
          <div class="wire-box"><div class="wire-label">Stage chips (scroll)</div>New · Qual · Meet · Prop · Hold…</div>
          <div class="wire-box tall"><div class="wire-label">Cards in selected stage</div>Ada Y. · 8–12M · Meta</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab">Home</div>
          <div class="ph-tab active">Sales</div>
          <div class="ph-tab">Inv</div>
          <div class="ph-tab">More</div>
        </div>
      </div>`,
    mobile: [
      "Horizontal stage selector; one column visible at a time",
      "Swipe between stages optional; List view default for bulk",
      "Drawer becomes full-screen sheet",
      "Match panel: vertical mini-cards with Hold/View",
    ],
    journey: ["New lead card", "Qualify", "Meeting", "Proposal", "Soft hold", "Reserve → Win"],
    journeyNote: "Matching can start from board drawer, inventory card, or customer Matches tab — same panel contract.",
    actions: [
      ["Drag / Change stage", "Card or drawer", "Moves opportunity; gated stages confirm"],
      ["Match inventory", "Drawer / card", "Visual unit mini-cards + Hold"],
      ["Open customer", "Drawer", "Unified profile"],
      ["Set follow-up", "Drawer", "Updates urgency on card"],
      ["Mark Lost / Won", "Stage change", "Reason or closing checklist"],
    ],
    visible: [
      "Customer name · stage · owner",
      "Budget band / value · project interest / held unit",
      "Follow-up due · source (small)",
      "KPI: open, overdue, soft holds, closing this week",
    ],
    hidden: [
      "Full attribution payload · score internals",
      "Legal/reservation document fields until stage needs them",
      "Finance settlement details (post-Won handoff)",
    ],
    rationaleTitle: "Pipeline is the workspace, not a report",
    rationale:
      "Current sales surfaces bury matching and stage discipline. Kanban-first with a shared match panel makes soft holds and unit linkage obvious.",
    rationaleBullets: [
      "Reduces spreadsheet-first inventory hopping mid-deal",
      "Stage rules encode risk (holds, lost reasons) in UX",
      "List remains available for power bulk ops",
    ],
    prev: { href: "05-customer-profile.html", label: "05 Customer" },
    next: { href: "07-inventory.html", label: "07 Inventory" },
    nextHref: "07-inventory.html",
    nextLabel: "Inventory",
  },
  {
    file: "07-inventory.html",
    num: "07",
    title: "Inventory",
    status: "pending",
    lede: "Image-led unit cards with one primary availability status — table is a power toggle, not the default.",
    route: "/dashboard/inventory",
    audience: "Sales · inventory ops",
    primaryUi: "Visual cards · Table toggle",
    todayWork: [
      { role: "Salesperson", task: "Find an available 2+1 and soft-hold for today’s meeting", faster: "Image cards + one status chip; Hold/Match on the card face." },
      { role: "Marketer", task: "Pull hero units for campaign creative", faster: "Visual grid shows sellable stock without multi-status table noise." },
      { role: "Investor manager", task: "Confirm which units are truly available vs held", faster: "Single primary availability language matches Dashboard donut." },
      { role: "Executive", task: "Scan availability mix by project", faster: "Summary chips answer stock health; Advanced statuses stay in drawer." },
    ],
    todayPrinciple: "Sell what you can see. Table, legal IDs, and secondary construction statuses remain capable in Advanced — not on the default face.",
    wireIntro: "Project/building/floor tree filters a card grid. Primary status is a single chip; secondary statuses hide until hover/drawer.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>Inventory · [Cards ●] [Table]</span><span>Avail 120 · Reserved 34 · Sold 210 · Hold 12</span></div>
        <div class="wire-body">
          <div class="wire-nav">
            <div class="wire-label">Projects</div>
            <div class="item active">North Tow.</div>
            <div class="item">· B1</div>
            <div class="item">· B2</div>
            <div class="item">Marina</div>
            <div class="wire-label" style="margin-top:8px">Floors</div>
            <div class="item">10 11 12</div>
          </div>
          <div class="wire-main">
            <div class="wire-row">
              ${["A-1204|2+1 · 95m|9.2M|AVAILABLE", "A-1208|2+1 · 98m|9.8M|HOLD", "B-402|1+1 · 62m|6.1M|RESERVED", "B-410|3+1 · 140m|14.2M|SOLD"]
                .map((row) => {
                  const [a, b, c, d] = row.split("|");
                  return `<div class="wire-box tall" style="min-width:120px"><div class="wire-label">[ image ]</div><strong>${a}</strong><br/>${b}<br/>${c}<br/><span class="wire-chip">${d}</span></div>`;
                })
                .join("")}
            </div>
          </div>
        </div>
      </div>`,
    hifiIntro: "Property-software feel: large photos, clear price and status, match actions on hover.",
    mockup: "mockups/07-inventory-desktop.png",
    mockCaption: "High-fidelity desktop · Visual inventory grid with project tree and status summary.",
    desktop: [
      "Summary chips + optional mini donut (same contract as Dashboard)",
      "Left: project / building / floor filters",
      "Main: responsive card grid (image, id, beds, area, price, one status)",
      "Drawer: Overview | Pricing | History | Docs | Advanced ▸",
    ],
    density: [
      "One primary availability chip only on card face",
      "Construction/closing/leasing statuses in Advanced or hover",
      "Table toggle for bulk/power users",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Inventory</div>
        <div class="ph-body">
          <div class="wire-box"><div class="wire-label">Filters sheet</div>Project · Status</div>
          <div class="wire-box tall"><div class="wire-label">[image] A-1204</div>2+1 · 9.2M · AVAILABLE</div>
          <div class="wire-box tall"><div class="wire-label">[image] A-1208</div>HOLD</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab">Home</div>
          <div class="ph-tab">Sales</div>
          <div class="ph-tab active">Inv</div>
          <div class="ph-tab">More</div>
        </div>
      </div>`,
    mobile: [
      "Single-column image cards",
      "Filters in bottom sheet",
      "Tree becomes project picker",
      "Soft hold / Reserve as sticky drawer actions",
    ],
    journey: ["Browse / filter", "Open unit", "Match or Hold", "Return to Sales deal"],
    journeyNote: "Entry points: Sales match panel, Inventory card “Match to customer”, Customer Matches tab.",
    actions: [
      ["Soft hold / Reserve", "Card or drawer", "Status change + sales link"],
      ["Match to customer", "Card", "Opens match with unit fixed"],
      ["Release hold", "Hold card", "Returns to Available"],
      ["Toggle Table", "Header", "Power dense view"],
    ],
    visible: [
      "Unit id · project (+ building)",
      "Beds / typology · primary area",
      "List price + currency",
      "One primary availability status · thumbnail",
    ],
    hidden: [
      "legal_identifier · orientation · view · exterior split",
      "Release/delivery dates",
      "Construction / closing / leasing secondary statuses",
      "Long description · internal notes",
    ],
    rationaleTitle: "Sell what you can see",
    rationale:
      "Dense multi-status tables train nobody and hide the product. Image-led cards with one status match how agents pitch units.",
    rationaleBullets: [
      "Aligns inventory glance with Dashboard donut contract",
      "Keeps power table without making it the default",
      "Matching stays visual across Sales and Inventory",
    ],
    prev: { href: "06-sales-pipeline.html", label: "06 Sales" },
    next: { href: "08-project-cards.html", label: "08 Project Cards" },
    nextHref: "08-project-cards.html",
    nextLabel: "Project Cards",
  },
  {
    file: "08-project-cards.html",
    num: "08",
    title: "Project Cards",
    status: "pending",
    lede: "Portfolio as a visual gallery — cover, phase, unit progress, health — not a finance spreadsheet.",
    route: "/dashboard/projects",
    audience: "Sales · PMs · leadership glance",
    primaryUi: "Card grid · List toggle",
    todayWork: [
      { role: "Salesperson", task: "Open the project they are pitching today", faster: "Cover + unit progress make the right site obvious in seconds." },
      { role: "Marketer", task: "Pick at-risk or launch-ready projects for campaigns", faster: "Health badge surfaces risk without opening finance sheets." },
      { role: "Investor manager", task: "Brief stakeholders on portfolio progress", faster: "Unit progress + phase on cards — projections stay off the face." },
      { role: "Executive", task: "Spot the at-risk project before the weekly", faster: "Gallery scan beats a dense project admin table." },
    ],
    todayPrinciple: "Projects look like places. Finance and geo depth stay in detail Advanced — portfolio index stays operational.",
    wireIntro: "Three+ large cover cards communicate commercial health at a glance. Financial projections stay off the card face.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>Projects · [Cards ●] [List] · Status ▾ Priority ▾</span><span>[+ New]</span></div>
        <div class="wire-main">
          <div class="wire-row">
            ${[
              ["North Towers", "Construction · High", "210/400", "72%", "On track"],
              ["Marina Residences", "Sales · Medium", "40/120", "41%", "At risk"],
              ["Garden Villas", "Planning · Low", "—", "15%", "Early"],
            ]
              .map(
                ([n, p, u, pct, h]) =>
                  `<div class="wire-box tall" style="min-width:160px"><div class="wire-label">[ cover image ]</div><strong>${n}</strong><br/>${p}<br/>Units ${u}<br/>████ ${pct}<br/><span class="wire-chip">${h}</span></div>`
              )
              .join("")}
          </div>
        </div>
      </div>`,
    hifiIntro: "Image-led portfolio cards with progress and health — premium real-estate OS, not ops ERP.",
    mockup: "mockups/08-project-cards-desktop.png",
    mockCaption: "High-fidelity desktop · Project gallery with covers, progress, and health badges.",
    desktop: [
      "Filters: status, priority · Cards/List · + New",
      "Card: cover, name, phase/status + priority, unit progress, health, optional city/year",
      "Click → Project Detail",
      "Empty: create first project CTA",
    ],
    density: [
      "No financial projections on card",
      "Health badge is the risk signal; details explain why",
      "List toggle for dense comparison",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Projects</div>
        <div class="ph-body">
          <div class="wire-box tall"><div class="wire-label">[cover]</div>North Towers · 72% · On track</div>
          <div class="wire-box tall"><div class="wire-label">[cover]</div>Marina · At risk</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab">Home</div>
          <div class="ph-tab">Sales</div>
          <div class="ph-tab">Inv</div>
          <div class="ph-tab active">More</div>
        </div>
      </div>`,
    mobile: [
      "Single-column full-bleed covers",
      "Filters in sheet",
      "List rarely needed; cards default",
    ],
    journey: ["Browse portfolio", "Spot at-risk", "Open project", "Drill units or sales"],
    journeyNote: "Cards are the index; detail owns tabs for units, timeline, finance.",
    actions: [
      ["Open project", "Card", "Project detail"],
      ["+ New project", "Header", "Short create (5–8 fields)"],
      ["Filter status/priority", "Header", "Narrow portfolio"],
      ["Toggle List", "Header", "Dense compare"],
    ],
    visible: [
      "Cover · name · status/phase · priority",
      "Unit progress (sold/released vs total)",
      "Health badge · optional city / delivery year",
    ],
    hidden: [
      "Financial projections (~15 fields)",
      "Lat/long · ownership · dense cost breakdowns",
      "Full address / legal enums",
    ],
    rationaleTitle: "Projects should look like places",
    rationale:
      "Current project lists read like admin tables. Cover cards make the portfolio scannable for sales and leadership without training.",
    rationaleBullets: [
      "Commercial health (units + progress) before finance",
      "At-risk projects surface visually",
      "Create stays short; Advanced waits for detail",
    ],
    prev: { href: "07-inventory.html", label: "07 Inventory" },
    next: { href: "09-project-detail.html", label: "09 Project Detail" },
    nextHref: "09-project-detail.html",
    nextLabel: "Project Detail",
  },
  {
    file: "09-project-detail.html",
    num: "09",
    title: "Project Detail",
    status: "pending",
    lede: "One job on Overview: status of the project. Units, timeline, team, docs daily; Finance and Advanced role-gated.",
    route: "/dashboard/projects/[projectId]",
    audience: "PM · sales · restricted finance",
    primaryUi: "Hero + tabs",
    todayWork: [
      { role: "Salesperson", task: "See available units and soft holds for this project", faster: "Overview KPIs + Units tab reuse inventory cards — one mental model." },
      { role: "Marketer", task: "Check next milestone before a launch asset", faster: "Milestone + activity on Overview without digging permits." },
      { role: "Investor manager", task: "Review commercial pulse; open Finance only if permitted", faster: "Finance/Advanced tabs disclose depth — Overview stays daily." },
      { role: "Executive", task: "Answer “how is North Towers?” in one screen", faster: "Hero + sold/available/holds + progress — no domain dump." },
    ],
    todayPrinciple: "One job on Overview: project status. Backend finance and permits remain; UI hides them behind role-gated tabs.",
    wireIntro: "Hero cover strip, KPIs, progress, activity. Units tab embeds inventory cards filtered to the project — not a 6-status table.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>← Projects / North Towers</span><span>[Edit] [Add unit] [Upload]</span></div>
        <div class="wire-main">
          <div class="wire-box muted tall" style="min-height:48px"><div class="wire-label">[ hero / cover strip ]</div>North Towers · Construction · On track · Owner: PM Ayşe</div>
          <div style="border-bottom:1.5px solid #9aa3b5;padding-bottom:6px"><strong>Overview</strong> · Units · Timeline · Team · Docs · Finance ▸ · Advanced ▸</div>
          <div class="wire-row">
            <div class="wire-box"><div class="wire-label">Units sold</div><div class="wire-value">210/400</div></div>
            <div class="wire-box"><div class="wire-label">Available</div><div class="wire-value">120</div></div>
            <div class="wire-box"><div class="wire-label">Soft holds</div><div class="wire-value">12</div></div>
            <div class="wire-box"><div class="wire-label">Next milestone</div><div class="wire-value">Facade</div></div>
          </div>
          <div class="wire-box"><div class="wire-label">Progress 72%</div>Sales funnel mini → Sales filtered<br/>Recent: A-1204 reserved — Ada Yılmaz</div>
        </div>
      </div>`,
    hifiIntro: "Hero-led project home with calm KPIs — construction + sales pulse without packing permits and ROI into the default view.",
    mockup: "mockups/09-project-detail-desktop.png",
    mockCaption: "High-fidelity desktop · North Towers detail with hero, KPIs, and overview tabs.",
    desktop: [
      "Hero cover + title row (phase, health, PM) + primary actions",
      "Tabs with discipline: Overview daily; Finance/Advanced disclosed",
      "Overview KPIs + progress + mini funnel + activity",
      "Units tab = inventory card embed for this project",
    ],
    density: [
      "Avoid packing construction + permits + costs + sales into default",
      "Finance hidden for pure sales roles without permission",
      "Timeline is visual milestones, not spreadsheet-first",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">North Towers</div>
        <div class="ph-body">
          <div class="wire-box tall"><div class="wire-label">[hero]</div>On track · 72%</div>
          <div class="wire-row">
            <div class="wire-box"><div class="wire-value">210</div><div class="wire-label">Sold</div></div>
            <div class="wire-box"><div class="wire-value">120</div><div class="wire-label">Avail</div></div>
          </div>
          <div class="wire-box">Next: Facade</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab active">Overview</div>
          <div class="ph-tab">Units</div>
          <div class="ph-tab">More</div>
        </div>
      </div>`,
    mobile: [
      "Hero compresses to banner",
      "Tab chips scroll; Finance behind More if permitted",
      "Units = same inventory cards single column",
    ],
    journey: ["Open from cards", "Scan Overview", "Units or Timeline", "Finance if role"],
    journeyNote: "Sales funnel mini drills to Sales filtered by this project.",
    actions: [
      ["Edit project", "Header", "Daily fields; Advanced collapsed"],
      ["Add unit", "Header", "Inventory create scoped to project"],
      ["Upload doc", "Header / Docs", "Files tab"],
      ["Open unit", "Units tab", "Inventory drawer"],
      ["Drill Sales", "Mini funnel", "Pipeline filtered"],
    ],
    visible: [
      "Name, status, health, PM",
      "Units sold / available / soft holds",
      "Next milestone · recent activity · progress %",
    ],
    hidden: [
      "Geo lat/long · ownership · legal enums",
      "Budgets ROI/IRR equity debt (Finance tab)",
      "Permits · cost lines (Advanced / construction roles)",
      "Full sqft planning breakdowns on create",
    ],
    rationaleTitle: "Detail without the dump",
    rationale:
      "Project pages today over-expose every domain. Tab discipline and progressive Finance/Advanced let sales use the page daily.",
    rationaleBullets: [
      "Units reuse inventory visual language",
      "Role-gated finance prevents accidental overwhelm",
      "Overview answers “how is this project?” in one screen",
    ],
    prev: { href: "08-project-cards.html", label: "08 Project Cards" },
    next: { href: "10-marketing-home.html", label: "10 Marketing Home" },
    nextHref: "10-marketing-home.html",
    nextLabel: "Marketing Home",
  },
  {
    file: "10-marketing-home.html",
    num: "10",
    title: "Marketing Home",
    status: "pending",
    lede: "Replace the 30-item marketing rail with a calm production home: campaigns, audiences, content, calendar — Advanced for the rest.",
    route: "/dashboard/marketing",
    audience: "Marketing · growth",
    primaryUi: "KPI home + campaign list",
    todayWork: [
      { role: "Salesperson", task: "See which campaigns feed today’s leads", faster: "Campaign list + lead counts without living in Marketing rail." },
      { role: "Marketer", task: "Ship or continue this week’s campaign / content", faster: "Production + Content Studio link are the home job — not 30 nav items." },
      { role: "Investor manager", task: "Rarely lands here; when needed, channel health is honest", faster: "Empty states when disconnected — no fake engagement charts." },
      { role: "Executive", task: "Confirm marketing is producing, not tooling", faster: "Active campaigns · leads · content shipped — Advanced tools stay collapsed." },
    ],
    todayPrinciple: "Studio, not subway map. Deep advertising, attribution, and AI routes stay available under Advanced — chrome stops advertising them.",
    wireIntro: "Top tabs for primary work. Advanced ▾ holds advertising, attribution, forecasting, automations, vendors, AI — routes exist, chrome does not shout them.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>Marketing</span><span>[Campaigns] [Audiences] [Content Studio →] [Calendar] [Advanced ▾]</span></div>
        <div class="wire-main">
          <div class="wire-row">
            <div class="wire-box"><div class="wire-label">Active campaigns</div><div class="wire-value">4</div></div>
            <div class="wire-box"><div class="wire-label">Leads in period</div><div class="wire-value">86</div></div>
            <div class="wire-box"><div class="wire-label">Content shipped</div><div class="wire-value">12</div></div>
            <div class="wire-box"><div class="wire-label">Spend 7d</div><div class="wire-value">…</div></div>
          </div>
          <div class="wire-row">
            <div class="wire-box tall"><div class="wire-label">Production this week → Content Studio</div><div class="wire-bars"><div class="wire-bar" style="--w:70%"></div><div class="wire-bar" style="--w:55%"></div><div class="wire-bar" style="--w:40%"></div></div></div>
            <div class="wire-box tall"><div class="wire-label">Channel health</div>Site · Ads · Social · Email<br/><span style="font-size:10px">Honest empty if disconnected</span></div>
          </div>
          <div class="wire-box muted">Summer Launch — Active — 42 leads — [Open]<br/>Marina Awareness — Draft — [Continue]<br/>[+ New campaign]</div>
        </div>
      </div>`,
    hifiIntro: "Calm marketing ops home — production and campaigns first, power tools in Advanced.",
    mockup: "mockups/10-marketing-home-desktop.png",
    mockCaption: "High-fidelity desktop · Marketing home KPIs, production, channel health, campaigns.",
    desktop: [
      "Primary tabs: Campaigns, Audiences, Content Studio, Calendar, Advanced",
      "KPI row + production + channel health",
      "Campaign list/cards — wizard launched from + New, not on home",
      "Spend KPI only if finance permitted",
    ],
    density: [
      "No 12-step wizard on landing",
      "WhatsApp/SMS/forecasting/attribution/vendors/AI via Advanced or deep links",
      "Honest empty when channel not connected",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Marketing</div>
        <div class="ph-body">
          <div class="wire-row">
            <div class="wire-box"><div class="wire-value">4</div><div class="wire-label">Campaigns</div></div>
            <div class="wire-box"><div class="wire-value">86</div><div class="wire-label">Leads</div></div>
          </div>
          <div class="wire-box">Summer Launch · Active</div>
          <div class="wire-box">Content Studio →</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab">Home</div>
          <div class="ph-tab">Sales</div>
          <div class="ph-tab">Mkt</div>
          <div class="ph-tab active">More</div>
        </div>
      </div>`,
    mobile: [
      "KPI 2×2; campaign list primary scroll",
      "Content Studio as prominent link button",
      "Advanced behind More menu",
    ],
    journey: ["Check production", "Open campaign", "Ship content", "Advanced only if needed"],
    journeyNote: "Leaves default nav: WhatsApp, SMS, forecasting, attribution, vendor mgmt, multi-AI, 9 dashboard sub-routes.",
    actions: [
      ["Open campaign", "List", "Campaign detail / continue draft"],
      ["+ New campaign", "List", "Existing wizard, launched from here"],
      ["Go Content Studio", "Tab / production drill", "/dashboard/marketing/content"],
      ["Open Advanced tool", "Advanced ▾", "Deep route without primary chrome"],
    ],
    visible: [
      "Active campaigns count · leads in period · content shipped",
      "Campaign name / status / lead count",
      "Production by channel this week · channel health",
    ],
    hidden: [
      "Vendor / budget / attribution models",
      "AI prompt settings",
      "Approval workflow config",
      "Nine marketing dashboard sub-routes in primary nav",
    ],
    rationaleTitle: "Marketing should feel like a studio, not a subway map",
    rationale:
      "A 30-item rail guarantees training debt. A production home with Advanced restores focus while preserving deep routes.",
    rationaleBullets: [
      "Aligns GROW nav: Marketing + Content Studio",
      "Honest channel empties beat fake engagement charts",
      "Wizard stays; it just stops owning the home",
    ],
    prev: { href: "09-project-detail.html", label: "09 Project Detail" },
    next: { href: "11-content-studio.html", label: "11 Content Studio" },
    nextHref: "11-content-studio.html",
    nextLabel: "Content Studio",
  },
  {
    file: "11-content-studio.html",
    num: "11",
    title: "Content Studio",
    status: "pending",
    lede: "One studio for blog, social, email, templates, and assets — editor with progressive SEO/UTM details.",
    route: "/dashboard/marketing/content",
    audience: "Marketing content · approvals",
    primaryUi: "Card grid + editor",
    todayWork: [
      { role: "Salesperson", task: "Reuse published assets when talking to a prospect", faster: "Published cards + assets tab — not a separate CMS scavenger hunt." },
      { role: "Marketer", task: "Finish draft → submit / schedule / publish today", faster: "Status cards + editor meta rail; SEO/UTM behind Details ▸." },
      { role: "Investor manager", task: "Approve investor-facing copy when in the loop", faster: "Needs approve status makes the queue visible without workflow config." },
      { role: "Executive", task: "Confirm content is shipping on schedule", faster: "Scheduled / published cards answer production — not channel dashboards." },
    ],
    todayPrinciple: "One studio to ship. Landing builders, Design Studio furniture, and AI prompt settings stay out of the default path; backends remain.",
    wireIntro: "Channel tabs and status cards default. Create ▾ maps blog, social, email, from template. Landing pages/forms stay Advanced under Marketing; Design Studio furniture stays out.",
    wireHtml: `
      <div class="wire-frame">
        <div class="wire-top"><span>Marketing / Content Studio · [All] [Blog] [Social] [Email] [Templates] [Assets]</span><span>[+ Create ▾]</span></div>
        <div class="wire-main">
          <div class="wire-row">
            ${[
              ["Draft", "Marina guide", "Blog · Selim", "Updated 2h"],
              ["Scheduled", "Summer reel", "Social · Ayşe", "Thu 10:00"],
              ["Published", "ROI tips", "Blog", "18 Jul"],
              ["Needs approve", "Email #12", "Email", "Waiting"],
            ]
              .map(
                ([st, t, m, when]) =>
                  `<div class="wire-box tall" style="min-width:120px"><div class="wire-label">${st}</div><strong>${t}</strong><br/>${m}<br/>${when}</div>`
              )
              .join("")}
          </div>
          <div class="wire-box muted"><div class="wire-label">Editor</div>Title + body/blocks | Status · Channel · Campaign · Schedule · Approvals · SEO/UTM (Details ▸) · Save / Submit / Publish</div>
        </div>
      </div>`,
    hifiIntro: "Editorial card grid with clear status — create and approve without a second marketing OS.",
    mockup: "mockups/11-content-studio-desktop.png",
    mockCaption: "High-fidelity desktop · Content Studio cards across draft/scheduled/published/approval.",
    desktop: [
      "Channel tabs + search + status filter + Create ▾",
      "Cards default; list/table for bulk",
      "Editor: canvas left, meta rail right with Details ▸ for SEO/UTM",
      "Actions: Save, Submit, Publish",
    ],
    density: [
      "Landing pages/forms not default studio clutter",
      "Design Studio (furniture product) explicitly excluded",
      "Disconnected channel → honest banner, no fake metrics",
    ],
    mobileWire: `
      <div class="wire-phone">
        <div class="ph-top">Content Studio</div>
        <div class="ph-body">
          <div class="wire-box"><div class="wire-label">Channel chips</div>All Blog Social Email</div>
          <div class="wire-box tall">Draft · Marina guide</div>
          <div class="wire-box tall">Scheduled · Summer reel</div>
        </div>
        <div class="ph-tabbar">
          <div class="ph-tab">Library</div>
          <div class="ph-tab active">Create</div>
          <div class="ph-tab">More</div>
        </div>
      </div>`,
    mobile: [
      "Cards single column; editor full-screen",
      "Meta rail becomes bottom sheet",
      "Approvals as banner on card",
    ],
    journey: ["Filter channel", "Create or open draft", "Edit", "Submit / Schedule / Publish"],
    journeyNote: "Empty: “Create your first piece — blog, social, or email.”",
    actions: [
      ["Create ▾", "Header", "Blog / Social / Email / From template"],
      ["Submit for approval", "Editor", "Needs approve status"],
      ["Schedule / Publish", "Editor", "Channel publish path"],
      ["Open Assets", "Tab", "Media library"],
    ],
    visible: [
      "Title · channel type · status",
      "Owner · updated / schedule time",
      "Linked campaign (optional)",
    ],
    hidden: [
      "SEO / UTM (Details drawer)",
      "Approval workflow configuration",
      "Vendor/budget/attribution (Marketing Advanced)",
      "AI prompt settings (AI restricted)",
    ],
    rationaleTitle: "Ship content from one place",
    rationale:
      "Blog, social, and email lived in separate rails and workspaces. Content Studio consolidates creation while leaving product Design Studio and landing-page builders out of the way.",
    rationaleBullets: [
      "Matches GROW nav item under Marketing",
      "Progressive disclosure keeps editor calm",
      "Honest empties and channel banners build trust",
    ],
    prev: { href: "10-marketing-home.html", label: "10 Marketing" },
    next: { href: "index.html", label: "Package index" },
    nextHref: "index.html",
    nextLabel: "Package index",
  },
];

for (const s of screens) {
  fs.writeFileSync(path.join(__dirname, s.file), screenPage(s), "utf8");
  console.log("wrote", s.file);
}

// --- 03 Navigation IA ---
const nav03 =
  head("UXR1 · Section 03 — Navigation / Information Architecture · INVESTHOME OS") +
  topline(`<span class="badge pending">PENDING REVIEW</span>`) +
  `
  <header class="hero">
    <div class="eyebrow">Section 03 · Navigation / IA</div>
    <h1>Proposed information architecture</h1>
    <p class="lede">Hide technical platform modules from normal users. Eliminate dual CRM/Marketing rails. Deep tools open as in-page sections — not a second sidebar.</p>
    <div class="meta-row">
      <span><strong>Source</strong> <code>03-proposed-navigation.md</code></span>
      <span><strong>Rule</strong> Preserve backends · hide in chrome</span>
    </div>
    <nav class="toc">
      <a href="#compare">Current vs proposed</a>
      <a href="#primary">Primary tree</a>
      <a href="#restricted">Restricted</a>
      <a href="#routes">Routes &amp; permissions</a>
      <a href="#removed">Removed from nav</a>
    </nav>
  </header>

  <section id="compare">
    <div class="section-head">
      <h2>Current vs proposed</h2>
      <span class="section-note">Visual tree comparison</span>
    </div>
    <div class="tree-compare">
      <div class="tree">
        <h3>Current (pain)</h3>
        <ul>
          <li><div class="group">Competing homes</div>
            <div class="leaf strike">CRM workspace rail</div>
            <div class="leaf strike">Marketing 30-item rail</div>
            <div class="leaf strike">BI explorer as peer</div>
            <div class="leaf strike">Executive as separate top item</div>
            <div class="leaf strike">Activity / Onboarding / Company tree in primary</div>
          </li>
          <li><div class="group">Platform noise</div>
            <div class="leaf strike">Automation</div>
            <div class="leaf strike">Design Studio (product) in staff OS</div>
            <div class="leaf strike">G15 platform children</div>
          </li>
        </ul>
      </div>
      <div class="tree proposed">
        <h3>Proposed (target)</h3>
        <ul>
          <li><div class="group">Command</div><div class="leaf primary">Dashboard</div></li>
          <li><div class="group">Work</div>
            <div class="leaf primary">Customers</div>
            <div class="leaf primary">Sales</div>
            <div class="leaf primary">Inventory</div>
            <div class="leaf primary">Projects</div>
          </li>
          <li><div class="group">Grow</div>
            <div class="leaf primary">Marketing</div>
            <div class="leaf primary">Content Studio</div>
          </li>
          <li><div class="group">Coordinate</div>
            <div class="leaf primary">Calendar · Tasks · Documents · Reports</div>
          </li>
          <li><div class="group">Secondary (role-gated)</div>
            <div class="leaf dim">Finance · AI · Settings</div>
          </li>
          <li><div class="group">Admin only</div>
            <div class="leaf dim">Admin (users, roles, platform collapsed)</div>
          </li>
        </ul>
      </div>
    </div>
  </section>

  <section id="primary">
    <div class="section-head"><h2>Primary navigation groups</h2></div>
    <div class="ia-grid">
      <div class="ia-group">
        <div class="ia-label">Command</div>
        <ul><li>Dashboard<span>/dashboard</span></li></ul>
      </div>
      <div class="ia-group">
        <div class="ia-label">Work</div>
        <ul>
          <li>Customers<span>/dashboard/customers</span></li>
          <li>Sales<span>/dashboard/sales</span></li>
          <li>Inventory<span>/dashboard/inventory</span></li>
          <li>Projects<span>/dashboard/projects</span></li>
        </ul>
      </div>
      <div class="ia-group">
        <div class="ia-label">Grow</div>
        <ul>
          <li>Marketing<span>/dashboard/marketing</span></li>
          <li>Content Studio<span>/dashboard/marketing/content</span></li>
        </ul>
      </div>
      <div class="ia-group">
        <div class="ia-label">Coordinate</div>
        <ul>
          <li>Calendar<span>/dashboard/calendar</span></li>
          <li>Tasks<span>/dashboard/tasks</span></li>
          <li>Documents<span>/dashboard/documents</span></li>
          <li>Reports<span>/dashboard/reports</span></li>
        </ul>
      </div>
    </div>
  </section>

  <section id="restricted">
    <div class="section-head"><h2>Restricted &amp; admin</h2></div>
    <div class="ia-grid" style="grid-template-columns:1fr 1fr 1fr">
      <div class="ia-group restricted">
        <div class="ia-label">Secondary · role-gated</div>
        <ul>
          <li>Finance<span>finance view</span></li>
          <li>AI<span>AI workspace view</span></li>
          <li>Settings<span>settings/company</span></li>
        </ul>
      </div>
      <div class="ia-group admin">
        <div class="ia-label">Admin only</div>
        <ul>
          <li>Admin<span>users · roles · platform collapsed</span></li>
        </ul>
      </div>
      <div class="ia-group removed">
        <div class="ia-label">Out of normal nav</div>
        <ul>
          <li>CRM / Marketing dual rails</li>
          <li>BI explorer · Automation</li>
          <li>Design Studio product · G15 children</li>
          <li>Onboarding → Help menu</li>
        </ul>
      </div>
    </div>
  </section>

  <section id="routes">
    <div class="section-head"><h2>Item → route → permission</h2></div>
    <div class="panel">
      <table>
        <thead><tr><th>Label</th><th>Route</th><th>Min permission (proposal)</th></tr></thead>
        <tbody>
          <tr><td>Dashboard</td><td><code>/dashboard</code></td><td>authenticated</td></tr>
          <tr><td>Customers</td><td><code>/dashboard/customers</code></td><td>customers/leads/investors view (unified)</td></tr>
          <tr><td>Sales</td><td><code>/dashboard/sales</code></td><td>sales/leads view</td></tr>
          <tr><td>Inventory</td><td><code>/dashboard/inventory</code></td><td>inventory view</td></tr>
          <tr><td>Projects</td><td><code>/dashboard/projects</code></td><td>projects view</td></tr>
          <tr><td>Marketing</td><td><code>/dashboard/marketing</code></td><td>marketing view</td></tr>
          <tr><td>Content Studio</td><td><code>/dashboard/marketing/content</code></td><td>marketing content view</td></tr>
          <tr><td>Calendar</td><td><code>/dashboard/calendar</code></td><td>calendar/tasks view</td></tr>
          <tr><td>Tasks</td><td><code>/dashboard/tasks</code></td><td>tasks view</td></tr>
          <tr><td>Documents</td><td><code>/dashboard/documents</code></td><td>documents/knowledge view</td></tr>
          <tr><td>Reports</td><td><code>/dashboard/reports</code></td><td>reports or analytics (narrow)</td></tr>
          <tr><td>Finance</td><td><code>/dashboard/finance</code></td><td>finance view</td></tr>
          <tr><td>AI</td><td><code>/dashboard/ai</code></td><td>AI workspace view</td></tr>
          <tr><td>Settings</td><td><code>/dashboard/settings</code></td><td>settings/company view</td></tr>
          <tr><td>Admin</td><td><code>/dashboard/admin</code></td><td>admin</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section id="removed">
    <div class="section-head"><h2>Secondary rails proposal</h2></div>
    <div class="callout">
      <h3>Eliminate dual CRM/Marketing rails for normal users</h3>
      <p>Deep tools open as <strong>in-page sections / tabs</strong>, not a second sidebar. Power users may later get an “Advanced” toggle (post-approval). Routes still exist; chrome stops advertising them.</p>
    </div>
  </section>

  <div class="checkpoint">
    <div class="eyebrow">Approval gate</div>
    <h2>Section 03 ready for review</h2>
    <p>Canonical nav model for UXR1. Approve with wireframes 04–11 before any implementation.</p>
    <div class="actions">
      <a class="btn" href="index.html">Package index</a>
      <a class="btn ghost" href="04-dashboard.html">Next: Dashboard wireframe</a>
    </div>
  </div>
` +
  foot(
    { href: "02-simplification-proposal.html", label: "02 Proposal" },
    { href: "04-dashboard.html", label: "04 Dashboard" }
  );

fs.writeFileSync(path.join(__dirname, "03-navigation-ia.html"), nav03, "utf8");
console.log("wrote 03-navigation-ia.html");

// --- Index ---
const indexItems = [
  { num: "00", title: "UX Principles", href: "00-ux-principles.html", status: "pending", blurb: "Operational product rules for every screen." },
  { num: "01", title: "UX Audit", href: "01-ux-audit.html", status: "conditional", blurb: "Current pain, density, training debt." },
  { num: "02", title: "Simplification Proposal", href: "02-simplification-proposal.html", status: "approved", blurb: "Merge / hide / keep model — APPROVED." },
  { num: "03", title: "Navigation / IA", href: "03-navigation-ia.html", status: "pending", blurb: "Primary vs restricted tree." },
  { num: "04", title: "Dashboard", href: "04-dashboard.html", status: "pending", blurb: "Today + funnel + availability." },
  { num: "05", title: "Customer Profile", href: "05-customer-profile.html", status: "pending", blurb: "Unified person journey." },
  { num: "06", title: "Sales Pipeline", href: "06-sales-pipeline.html", status: "pending", blurb: "Kanban + matching." },
  { num: "07", title: "Inventory", href: "07-inventory.html", status: "pending", blurb: "Image-led unit cards." },
  { num: "08", title: "Project Cards", href: "08-project-cards.html", status: "pending", blurb: "Visual portfolio gallery." },
  { num: "09", title: "Project Detail", href: "09-project-detail.html", status: "pending", blurb: "Overview tab discipline." },
  { num: "10", title: "Marketing Home", href: "10-marketing-home.html", status: "pending", blurb: "Calm production home." },
  { num: "11", title: "Content Studio", href: "11-content-studio.html", status: "pending", blurb: "Blog · social · email studio." },
  { num: "12", title: "Design System Recs", href: "12-design-system-recommendations.html", status: "pending", blurb: "Tokens, patterns, chart exceptions." },
  { num: "13", title: "Implementation Roadmap", href: "13-implementation-roadmap.html", status: "pending", blurb: "Design-only phases · no code yet." },
];

const statusBadge = (s) =>
  s === "approved"
    ? `<span class="badge ok">Approved</span>`
    : s === "conditional"
      ? `<span class="badge warn">Conditional</span>`
      : `<span class="badge pending">Pending</span>`;

const indexHtml =
  head("UXR1 Review Package · INVESTHOME OS") +
  topline(`<span class="badge gate">WAITING FOR FINAL PRODUCT REVIEW</span>`) +
  `
  <header class="hero">
    <div class="eyebrow">UXR1 · Complete review package</div>
    <h1>Simplification review — ready for product sign-off</h1>
    <p class="lede">Clickable index for principles, audit, approved proposal, IA, wireframes 04–11 (low-fi, hi-fi, desktop, mobile, journeys, fields, Today's work), design-system recommendations, and a design-only roadmap. <strong>No production code. Waiting for final product review — no implementation.</strong></p>
    <div class="meta-row">
      <span><strong>S1</strong> Conditional</span>
      <span><strong>S2</strong> Approved</span>
      <span><strong>S3–11</strong> Pending product review</span>
      <span><strong>S12–13</strong> Pending</span>
      <span><strong>Implementation</strong> Blocked</span>
    </div>
  </header>

  <section>
    <div class="section-head">
      <h2>Package contents</h2>
      <span class="section-note">Open each section · approve before code</span>
    </div>
    <div class="index-grid">
      ${indexItems
        .map(
          (i) => `
      <a class="index-card" href="${i.href}">
        <div class="num">Section ${i.num}</div>
        <h3>${i.title}</h3>
        <p>${i.blurb}</p>
        ${statusBadge(i.status)}
      </a>`
        )
        .join("")}
    </div>
  </section>

  <section>
    <div class="section-head"><h2>Per-screen checklist (04–11)</h2></div>
    <div class="panel">
      <table>
        <thead><tr><th>Artifact</th><th>Included</th></tr></thead>
        <tbody>
          <tr><td>Today's work role callout</td><td>Salesperson · Marketer · Investor manager · Executive</td></tr>
          <tr><td>Low-fidelity wireframe</td><td>HTML box layouts</td></tr>
          <tr><td>High-fidelity mockup</td><td>PNG under <code>mockups/</code></td></tr>
          <tr><td>Desktop composition</td><td>Layout + density notes</td></tr>
          <tr><td>Mobile behavior / preview</td><td>Phone frame + rules</td></tr>
          <tr><td>User journey</td><td>Step strip</td></tr>
          <tr><td>Primary actions</td><td>Action table</td></tr>
          <tr><td>Visible &amp; hidden fields</td><td>Progressive disclosure</td></tr>
          <tr><td>Design rationale</td><td>Why better than current</td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-head"><h2>High-fidelity mockups</h2></div>
    <div class="panel">
      <table>
        <thead><tr><th>Screen</th><th>Asset</th></tr></thead>
        <tbody>
          <tr><td>04 Dashboard</td><td><code>mockups/04-dashboard-desktop.png</code></td></tr>
          <tr><td>05 Customer Profile</td><td><code>mockups/05-customer-profile-desktop.png</code></td></tr>
          <tr><td>06 Sales Pipeline</td><td><code>mockups/06-sales-pipeline-desktop.png</code></td></tr>
          <tr><td>07 Inventory</td><td><code>mockups/07-inventory-desktop.png</code></td></tr>
          <tr><td>08 Project Cards</td><td><code>mockups/08-project-cards-desktop.png</code></td></tr>
          <tr><td>09 Project Detail</td><td><code>mockups/09-project-detail-desktop.png</code></td></tr>
          <tr><td>10 Marketing Home</td><td><code>mockups/10-marketing-home-desktop.png</code></td></tr>
          <tr><td>11 Content Studio</td><td><code>mockups/11-content-studio-desktop.png</code></td></tr>
        </tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="callout">
      <h3>Design direction</h3>
      <p>Real production product for real-estate sales &amp; marketing — not a generic admin template. Prefer operational workflows over data density. Advanced capabilities via progressive disclosure. Backend remains capable; UI hides complexity. Light · visual · spacious · teal-slate accent. Avoid purple AI slop and dark trading-terminal aesthetics.</p>
    </div>
  </section>

  <div class="checkpoint">
    <div class="eyebrow">Final approval gate</div>
    <h2>WAITING FOR FINAL PRODUCT REVIEW — NO IMPLEMENTATION</h2>
    <p>Do not change routes, apps/web, or apps/api until explicit written approval of this full UXR1 package. This deliverable is visual review only.</p>
    <div class="actions">
      <a class="btn" href="00-ux-principles.html">Start at UX Principles</a>
      <a class="btn ghost" href="02-simplification-proposal.html">Revisit approved S2</a>
      <a class="btn ghost" href="13-implementation-roadmap.html">Design-only roadmap</a>
    </div>
  </div>
</div>
</body>
</html>
`;

fs.writeFileSync(path.join(__dirname, "index.html"), indexHtml, "utf8");
console.log("wrote index.html");
console.log("done");
