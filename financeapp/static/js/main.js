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
