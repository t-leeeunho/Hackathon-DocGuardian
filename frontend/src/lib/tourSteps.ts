/**
 * First-run onboarding tour. Each step spotlights a *functional* region of the
 * workspace (located by its `data-tour` anchor in `AppShell`) and explains what
 * it does and what you can do with it — so a brand-new user immediately sees the
 * interactive parts of DocGuardian. Keep the copy short and action-oriented.
 */
export interface TourStep {
  /** `data-tour` anchor to highlight. */
  anchor: string;
  title: string;
  body: string;
}

export const tourSteps: TourStep[] = [
  {
    anchor: 'graph',
    title: 'Your living knowledge graph',
    body: 'Every document is a node — colour is health (green = fresh, yellow = aging, red = stale or conflicting) and size is importance. No human drew these links; DocGuardian infers them. Click any node to inspect it.',
  },
  {
    anchor: 'chat',
    title: 'Ask your docs anything',
    body: 'Ask a question in plain English and get a grounded answer with citations and a confidence score — or an honest “needs review” when the evidence is weak. The sources it used glow on the graph. Evidence or silence.',
  },
  {
    anchor: 'intake',
    title: 'Drop in new docs',
    body: 'Paste text or a website URL and DocGuardian ingests it: the Librarian rewrites it into a clean, canonical form and files it automatically. Your original is always preserved.',
  },
  {
    anchor: 'insights',
    title: 'Corpus & document insights',
    body: 'Open Insights for stale, duplicate and broken-link trends across the whole corpus — plus a per-document breakdown of quality, links and staleness risk.',
  },
  {
    anchor: 'metrics',
    title: 'Governance at a glance',
    body: 'These live counters track what DocGuardian has detected and fixed — stale pages, conflicts, duplicates and broken links. Every change is human-approved and recorded with provenance.',
  },
];
