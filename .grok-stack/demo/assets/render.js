const ids = ["route", "spec", "architecture", "governance", "verification"];

function element(id) {
  return document.getElementById(id);
}

function setText(target, value) {
  target.textContent = value === null || value === undefined ? "—" : String(value);
}

function label(value) {
  return String(value || "unknown").replaceAll("_", " ");
}

function shortDigest(value) {
  return typeof value === "string" && value.length > 16 ? `${value.slice(0, 10)}…${value.slice(-6)}` : value;
}

function setStatus(name, status) {
  const target = element(`${name}-status`);
  const normalized = status === "complete" || status === "ready" ? "pass" : status;
  target.className = `status-badge status-${normalized}`;
  setText(target, label(status));
}

function metric(content, term, value) {
  const group = document.createElement("div");
  const name = document.createElement("dt");
  const result = document.createElement("dd");
  setText(name, term);
  if (Array.isArray(value)) {
    setText(result, value.length ? value.join(" · ") : "None");
  } else {
    setText(result, value);
  }
  group.append(name, result);
  content.append(group);
}

function provenance(name, panel) {
  const target = element(`${name}-provenance`);
  const source = label(panel.source);
  const digest = shortDigest(panel.digest);
  setText(target, digest ? `Source: ${source} · Digest: ${digest}` : `Source: ${source}`);
}

function unavailable(name, panel) {
  setStatus(name, panel.status);
  const content = element(`${name}-content`);
  content.replaceChildren();
  metric(content, "Unavailable", panel.error?.message || "Repository model is unavailable.");
  provenance(name, panel);
}

function renderRoute(panel) {
  const content = element("route-content");
  content.replaceChildren();
  metric(content, "Intent", label(panel.intent));
  metric(content, "Risk", label(panel.risk));
  metric(content, "Complexity", label(panel.complexity));
  metric(content, "Domains", panel.domains);
  metric(content, "Write owner", panel.write_agent || "No write owner");
  metric(content, "Workflow", panel.workflow_skills);
  setStatus("route", "pass");
  provenance("route", panel);
}

function renderSpec(panel) {
  if (panel.status === "unavailable") return unavailable("spec", panel);
  const content = element("spec-content");
  content.replaceChildren();
  metric(content, "Criteria", `${panel.criterion_mapped} / ${panel.criterion_total} mapped`);
  metric(content, "Invariants", panel.invariant_total);
  metric(content, "Forbidden outcomes", panel.forbidden_total);
  metric(content, "Objective", panel.objective?.statement);
  setStatus("spec", panel.status);
  provenance("spec", panel);
}

function renderArchitecture(panel) {
  if (panel.status === "unavailable") return unavailable("architecture", panel);
  const content = element("architecture-content");
  content.replaceChildren();
  metric(content, "Components", panel.node_count);
  metric(content, "Declared edges", panel.edge_count);
  metric(content, "Trust domains", panel.trust_domain_count);
  metric(content, "Contracts", panel.contract_count);
  setStatus("architecture", panel.status);
  provenance("architecture", panel);
}

function renderGovernance(panel) {
  if (panel.status === "unavailable") return unavailable("governance", panel);
  const content = element("governance-content");
  content.replaceChildren();
  metric(content, "Active rules", panel.active_rule_count);
  metric(content, "Candidate rules", panel.candidate_rule_count);
  metric(content, "Open debt", panel.open_debt_count);
  metric(content, "Canonical examples", panel.example_count);
  setStatus("governance", panel.status);
  provenance("governance", panel);
}

function renderVerification(panel) {
  const content = element("verification-content");
  content.replaceChildren();
  metric(content, "Passed", panel.pass);
  metric(content, "Failed", panel.fail);
  metric(content, "Skipped", panel.skip);
  metric(content, "Scope", panel.status === "not_run" ? "Draft route/spec preview — verification not run" : "Bundled sample evidence");
  setStatus("verification", panel.status);
  provenance("verification", panel);
}

export function renderSnapshot(snapshot, {stale = false} = {}) {
  renderRoute(snapshot.route);
  renderSpec(snapshot.spec);
  renderArchitecture(snapshot.architecture);
  renderGovernance(snapshot.governance);
  renderVerification(snapshot.verification);
  const statuses = ids.slice(1).map((name) => snapshot[name].status);
  const incomplete = statuses.some((status) => status === "fail" || status === "unavailable");
  const overall = stale ? "stale" : incomplete ? "incomplete" : snapshot.mode === "computed_preview" ? "draft" : "ready";
  setStatus("overall", overall);
  setText(element("results-heading"), snapshot.mode === "computed_preview" ? "Computed control preview" : "Reviewed sample control path");
  setText(element("mode-chip"), snapshot.mode === "computed_preview" ? "Computed preview" : "Bundled sample");
  element("results").setAttribute("aria-busy", "false");
}

export function renderLoading() {
  element("results").setAttribute("aria-busy", "true");
  setText(element("results-heading"), "Loading local evidence");
  setText(element("live-status"), "Loading local evidence");
}

export function announce(message) {
  setText(element("live-status"), message);
}
