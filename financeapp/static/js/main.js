/* FinanceOS — Main JavaScript */

document.addEventListener('DOMContentLoaded', () => {

  // ── Bootstrap Toasts ────────────────────────────────────────────────────────
  document.querySelectorAll('.toast').forEach(el => {
    new bootstrap.Toast(el, { delay: 4000 }).show();
  });

  // ── Sidebar Toggle ──────────────────────────────────────────────────────────
  const sidebar  = document.getElementById('sidebar');
  const toggle   = document.getElementById('sidebarToggle');
  const overlay  = document.getElementById('sidebarOverlay');

  function openSidebar()  { sidebar?.classList.add('open'); overlay?.classList.add('show'); }
  function closeSidebar() { sidebar?.classList.remove('open'); overlay?.classList.remove('show'); }

  toggle?.addEventListener('click', () => sidebar?.classList.contains('open') ? closeSidebar() : openSidebar());
  overlay?.addEventListener('click', closeSidebar);

  // ── Theme Toggle ────────────────────────────────────────────────────────────
  const themeBtn = document.getElementById('themeToggle');
  themeBtn?.addEventListener('click', async () => {
    const res = await fetch('/api/toggle-theme', { method: 'POST' });
    const data = await res.json();
    document.documentElement.setAttribute('data-theme', data.theme);
    const icon = themeBtn.querySelector('i');
    icon.className = data.theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
  });

  // ── Spending Tip Loader ─────────────────────────────────────────────────────
  const tipEl = document.getElementById('spendingTip');
  if (tipEl) {
    fetch('/api/spending-tip')
      .then(r => r.json())
      .then(data => {
        const label = tipEl.querySelector('.tip-label');
        const text  = tipEl.querySelector('.tip-text');
        if (label && data.category) label.textContent = `Top Expense: ${data.category}`;
        if (text) text.textContent = data.tip;
      })
      .catch(() => {});
  }

  // ── Number Counter Animation ────────────────────────────────────────────────
  document.querySelectorAll('[data-count]').forEach(el => {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const duration = 900;
    const start = performance.now();
    const isNeg = target < 0;
    const absTarget = Math.abs(target);

    function update(now) {
      const elapsed = now - start;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const val = absTarget * eased;
      el.textContent = prefix + (isNeg ? '-' : '') + val.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + suffix;
      if (progress < 1) requestAnimationFrame(update);
    }
    requestAnimationFrame(update);
  });

  // ── Progress Bar Animate ────────────────────────────────────────────────────
  setTimeout(() => {
    document.querySelectorAll('.prog-fill[data-width]').forEach(el => {
      el.style.width = el.dataset.width + '%';
    });
  }, 200);

});

// ── Chart Defaults ──────────────────────────────────────────────────────────
if (typeof Chart !== 'undefined') {
  Chart.defaults.font.family = "'DM Sans', sans-serif";
  Chart.defaults.color = '#8B90A6';
  Chart.defaults.plugins.legend.labels.usePointStyle = true;
  Chart.defaults.plugins.legend.labels.pointStyleWidth = 8;
}

// ── Utility: Build overview bar chart ────────────────────────────────────────
function buildBarChart(canvasId, labels, datasets, opts = {}) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'bar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'top' },
        tooltip: { mode: 'index', intersect: false }
      },
      scales: {
        x: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: { color: '#8B90A6' }
        },
        y: {
          grid: { color: 'rgba(255,255,255,0.05)' },
          ticks: {
            color: '#8B90A6',
            callback: v => '₹' + v.toLocaleString()
          }
        }
      },
      ...opts
    }
  });
}

function buildLineChart(canvasId, labels, datasets) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' } },
        y: {
          grid: { color: 'rgba(255,255,255,0.04)' },
          ticks: { callback: v => '₹' + v.toLocaleString() }
        }
      }
    }
  });
}

function buildDoughnutChart(canvasId, labels, data, colors) {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors,
        borderWidth: 2,
        borderColor: 'transparent',
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: { position: 'right' }
      }
    }
  });
}



/* ── AI Floating Drawer ─────────────────────────────── */
;(function() {
  const fab         = document.getElementById('aiFab');
  const drawer      = document.getElementById('aiDrawer');
  const drawerClose = document.getElementById('aiDrawerClose');
  const drawerInput = document.getElementById('aiDrawerInput');
  const drawerSend  = document.getElementById('aiDrawerSend');
  const drawerMsgs  = document.getElementById('aiDrawerMessages');
  if (!fab || !drawer) return;

  const drawerHistory = [];
  let drawerStreaming  = false;

  function md(t) {
    return t.replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
            .replace(/`(.+?)`/g,'<code style="background:var(--bg-4);padding:1px 5px;border-radius:3px;font-size:12px">$1</code>')
            .replace(/^- (.+)$/gm,'• $1').replace(/\n/g,'<br>');
  }

  fab.addEventListener('click', () => { drawer.classList.add('open'); fab.style.display='none'; });
  drawerClose?.addEventListener('click', () => { drawer.classList.remove('open'); fab.style.display='grid'; });

  function addMsg(role, text) {
    const wrap = document.createElement('div');
    wrap.className = `ai-msg ${role==='user'?'user':''}`;
    const av = document.createElement('div');
    av.className = 'ai-msg-avatar';
    av.innerHTML = role==='ai' ? '<i class="bi bi-stars"></i>' : (window._uInit||'U');
    const bubble = document.createElement('div');
    bubble.className = 'ai-msg-bubble';
    if (role==='ai') bubble.innerHTML = md(text); else bubble.textContent = text;
    wrap.appendChild(av); wrap.appendChild(bubble);
    drawerMsgs?.appendChild(wrap);
    setTimeout(()=>{ if(drawerMsgs) drawerMsgs.scrollTop=drawerMsgs.scrollHeight; },30);
    return bubble;
  }

  function showTyping() {
    const w=document.createElement('div'); w.className='ai-msg'; w.id='dTyping';
    w.innerHTML=`<div class="ai-msg-avatar"><i class="bi bi-stars"></i></div>
      <div class="ai-msg-bubble"><div class="drawer-typing"><span></span><span></span><span></span></div></div>`;
    drawerMsgs?.appendChild(w);
    setTimeout(()=>{ if(drawerMsgs) drawerMsgs.scrollTop=drawerMsgs.scrollHeight; },30);
  }

  async function send(text) {
    if (!text.trim() || drawerStreaming) return;
    drawerStreaming=true; if(drawerSend) drawerSend.disabled=true;
    if(drawerInput) drawerInput.value='';
    addMsg('user', text.trim());
    drawerHistory.push({role:'user',content:text.trim()});
    showTyping();
    try {
      const resp = await fetch('/api/ai-chat',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({messages:drawerHistory.slice(0,-1), message:text.trim()})
      });
      document.getElementById('dTyping')?.remove();
      if (!resp.ok) throw new Error();
      const bubble = addMsg('ai',''); bubble.innerHTML='';
      let full='';
      const reader=resp.body.getReader(), decoder=new TextDecoder();
      while(true){
        const{done,value}=await reader.read(); if(done) break;
        full+=decoder.decode(value,{stream:true}); bubble.innerHTML=md(full);
        if(drawerMsgs) drawerMsgs.scrollTop=drawerMsgs.scrollHeight;
      }
      drawerHistory.push({role:'assistant',content:full});
    } catch(_){
      document.getElementById('dTyping')?.remove();
      addMsg('ai','⚠️ Something went wrong. Please try again.');
    } finally {
      drawerStreaming=false; if(drawerSend) drawerSend.disabled=false; if(drawerInput) drawerInput.focus();
    }
  }

  drawerSend?.addEventListener('click', ()=>send(drawerInput?.value||''));
  drawerInput?.addEventListener('keydown', e=>{ if(e.key==='Enter'){e.preventDefault();send(drawerInput.value);} });
})();
