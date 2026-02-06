/**
 * Converts technical decision/policy reasons into plain-language messages
 * for end users on dashboards.
 */
const FRIENDLY_REASONS: Array<{ pattern: RegExp | string; message: string }> = [
  // Authentication
  { pattern: /Low risk; avoid unnecessary friction\.?/i, message: "This payment looked safe, so we kept checkout smooth with no extra steps." },
  { pattern: /Low risk and passkey supported; prefer strongest low-friction auth\.?/i, message: "Safe transaction and the customer uses passkey — we used the smoothest secure option." },
  { pattern: /\[A\/B treatment\] Low risk; 3DS frictionless for experiment\.?/i, message: "This payment looked safe, so we used a light-touch security check (test group)." },
  { pattern: /High risk; require step-up authentication\.?/i, message: "This payment looked higher risk, so we asked for an extra security step to protect the customer." },
  { pattern: /\[A\/B treatment\] Medium risk; step-up challenge for experiment\.?/i, message: "Medium risk — we used an extra security step for this test." },
  { pattern: /Medium risk; attempt frictionless 3DS to improve issuer confidence\.?/i, message: "Medium risk — we ran a quick background security check so the bank could approve with confidence." },
  // Retry
  { pattern: /Max retry attempts reached\.?/i, message: "We've already tried the maximum number of times. No further automatic retries." },
  { pattern: /Recurring \+ soft decline; schedule retry with backoff\.?\s*(\[A\/B treatment\])?/i, message: "Subscription payment had a temporary issue. We'll try again later." },
  { pattern: /Transient issuer\/system decline; quick retry may recover\.?/i, message: "The bank or system had a brief hiccup. A quick retry might work." },
  { pattern: /\[A\/B treatment\] Soft decline; allow retry with backoff\.?/i, message: "Temporary decline — we're allowing another try later (test group)." },
  { pattern: /Not a recognized soft decline; avoid risky retries\.?/i, message: "This type of decline isn't safe to retry automatically." },
  // Routing
  { pattern: /\[A\/B treatment\] Secondary-first routing\.?/i, message: "We tried the backup payment route first (test)." },
  { pattern: /Baseline routing heuristic; cascade after initial attempt\.?/i, message: "We used our standard order: first choice first, then backup if needed." },
];

function normalizeInput(reason: string): string {
  return reason.replace(/\s+/g, " ").trim();
}

/**
 * Returns an end-user-friendly explanation of a decision reason.
 * Falls back to a cleaned version of the raw reason if no mapping exists.
 */
export function friendlyReason(rawReason: string | undefined | null): string {
  if (rawReason == null || rawReason === "") return "—";
  const normalized = normalizeInput(rawReason);
  for (const { pattern, message } of FRIENDLY_REASONS) {
    if (typeof pattern === "string") {
      if (normalized.toLowerCase().includes(pattern.toLowerCase())) return message;
    } else if (pattern.test(normalized)) {
      return message;
    }
  }
  // Fallback: soften technical terms for display
  return normalized
    .replace(/\s*\[A\/B treatment\]\s*/gi, " ")
    .replace(/3DS frictionless/gi, "light security check")
    .replace(/3DS/gi, "security check")
    .replace(/step-up (authentication|challenge)/gi, "extra security step")
    .replace(/frictionless/gi, "smooth")
    .replace(/issuer/gi, "bank")
    .replace(/backoff/gi, "later")
    .replace(/\s+/g, " ")
    .trim() || "Decision applied.";
}
