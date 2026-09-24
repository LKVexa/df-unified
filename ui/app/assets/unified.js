/* DF_Unified console page. Reads window.DF_UNIFIED_STATUS, written by `STATUS` / `VERIFY` into unified_status.js. */
window.DF_UNIFIED_PAGE = function (h) {
  const esc = h.esc, section = h.section;
  const S = window.DF_UNIFIED_STATUS;
  if (!S) {
    return `<div class="eyebrow">DF Unified System</div><div class="callout"><b>No unified status recorded yet.</b><br>Run <code>STATUS.cmd</code> (or <code>VERIFY.cmd --full</code>) in the DF_Unified folder; it writes <code>ui/app/assets/unified_status.js</code> and this page renders the recorded local result.</div>`;
  }
  const badge = s => `<span class="chip" style="font-weight:700;${s === 'PASS' ? '' : s === 'FAIL' ? 'outline:2px solid #ff6b6b' : 'opacity:.7'}">${esc(s)}</span>`;
  const members = S.members.map(m => `<div class="ovm"><div class="size">${esc(m.container)} · ${esc(m.id)} · ${esc(m.role)}</div><h3>${esc(m.embedded)}</h3><p>${esc(m.summary)}</p><div class="chips">${m.dialect ? `<span class="chip">${esc(m.dialect)}</span>` : ''}${m.domain ? `<span class="chip">${esc(m.domain)}</span>` : ''}<span class="chip">${m.present ? 'present' : 'ABSENT'}</span></div></div>`).join('');
  const ug = S.unified_gates.map(g => `<tr><td><code>${esc(g.id)}</code></td><td>${esc(g.name)}</td><td>${badge(g.status)}</td><td>${esc(g.seconds)}</td></tr>`).join('');
  const mg = Object.entries(S.member_recorded_gates).map(([c, v]) => { const t = v.totals || {}; return `<tr><td>${esc(c)}</td><td>${esc(t.passed)}</td><td>${esc(t.skipped)}</td><td>${esc(t.failed)}</td><td><code>${esc(v.executed_at_utc || '')}</code></td></tr>`; }).join('');
  const dist = Object.entries(S.capability_distribution).sort((a, b) => b[1] - a[1]).map(([k, v]) => `<div class="tax"><b>${esc(v)}</b><p>${esc(k)}</p></div>`).join('');
  const ov = S.overlays.map(o => `<tr><td><code>${esc(o.container)}/${esc(o.prefix)}</code></td><td>${esc(o.kind)}</td><td>${badge(o.status)}</td><td>${esc(o.note)}</td></tr>`).join('');
  const cb = S.claim_boundary.map(x => `<li>${esc(x)}</li>`).join('');
  const t = S.totals || {};
  return `<div class="eyebrow">DF Unified System · DFU0 · v${esc(S.unified_version)}</div>
<div class="hero"><div><h1>Five containers, one system</h1><p>DF_Unified binds DF_Small, DF_Medium, DF_Large and DF_Xtra_Large (execution plane) to DF_Fabric (federation control plane) by relative path. Members stay sealed and untouched; this layer proves they are the pinned bytes, that the shared adapter and core are a single artifact, that every unsealed overlay is declared, and drives every battery from one door.</p><div class="chips"><span class="chip">one CLI</span><span class="chip">seals untouched</span><span class="chip">overlays accounted</span><span class="chip">blockers inherited</span></div></div>
<div class="hero-box"><div class="label">Unified verdict</div><div class="value">${esc(S.verdict)}</div><div class="label hero-gap">Gates</div><div class="value">${esc(t.PASS || 0)} pass · ${esc(t.FAIL || 0)} fail · ${esc(t.SKIPPED || 0)} skipped</div><div class="label hero-gap">Measured</div><div class="value">${esc(S.executed_at_utc)}<br>${esc(S.host.platform)}</div></div></div>
${section('Unified gates', '01 · THIS HOST', 'U0–U5 run in seconds with no toolchain. U6/U7 delegate to each member’s own battery and run with VERIFY --full.', `<div class="table-wrap"><table><thead><tr><th>Gate</th><th>Statement</th><th>Result</th><th>s</th></tr></thead><tbody>${ug}</tbody></table></div>`)}
${section('Members', '02 · PLANES', 'Four execution nodes of two ISA lineages, one control plane. Images never move between nodes; sealed rows do.', `<div class="overview-grid">${members}</div>`)}
${section('Member batteries as shipped', '03 · RECORDED EVIDENCE', 'The totals each container recorded at assembly. U6/U7 re-measure them on this host.', `<div class="table-wrap"><table><thead><tr><th>Member</th><th>Pass</th><th>Skip</th><th>Fail</th><th>Recorded</th></tr></thead><tbody>${mg}</tbody></table></div>`)}
${section('Capability census', '04 · ALL LEDGERS', 'Every item from all five capability ledgers, counted by status. Nothing is promoted by combining.', `<div class="taxonomy">${dist}</div>`)}
${section('Overlays outside the seals', '05 · ACCOUNTED DRIFT', 'Content added to member folders after they were sealed. Declared here so U3 can tell accounted drift from tampering.', `<div class="table-wrap"><table><thead><tr><th>Path</th><th>Kind</th><th>Status</th><th>Note</th></tr></thead><tbody>${ov}</tbody></table></div>`)}
${section('Claim boundary', '06 · WHAT IS NOT CLAIMED', 'Inherited verbatim from the members.', `<div class="callout"><ul>${cb}</ul></div>`)}`;
};
