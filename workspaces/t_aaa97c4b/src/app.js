/* =====================================================
   HERMES DESIGN SYSTEM — Interactive JavaScript
   ===================================================== */

(function () {
  'use strict';

  // ==========================================
  // DOM References
  // ==========================================
  const root = document.documentElement;
  const themeToggle = document.getElementById('theme-toggle');
  const searchTrigger = document.getElementById('search-trigger');
  const searchModal = document.getElementById('search-modal');
  const searchInput = document.getElementById('search-input');
  const searchResults = document.getElementById('search-results');
  const mobileMenuBtn = document.getElementById('mobile-menu-btn');
  const integrationTabList = document.getElementById('integration-tab-list');

  // ==========================================
  // Theme Management
  // ==========================================
  function getTheme() {
    return root.getAttribute('data-theme') || 'light';
  }

  function setTheme(theme) {
    root.setAttribute('data-theme', theme);
    try { localStorage.setItem('hermes-theme', theme); } catch (e) {}
  }

  function toggleTheme() {
    const next = getTheme() === 'light' ? 'dark' : 'light';
    setTheme(next);
  }

  // Init theme from localStorage or system preference
  (function initTheme() {
    let saved;
    try { saved = localStorage.getItem('hermes-theme'); } catch (e) {}
    if (!saved) {
      saved = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    setTheme(saved);
  })();

  if (themeToggle) themeToggle.addEventListener('click', toggleTheme);

  // ==========================================
  // Search
  // ==========================================
  const searchData = [
    { title: 'Color Tokens', path: '#color-tokens', icon: '🎨', desc: 'Brand, neutral, and semantic color tokens' },
    { title: 'Typography Tokens', path: '#typography-tokens', icon: '🔤', desc: 'Font families, sizes, weights, and spacing' },
    { title: 'Spacing Tokens', path: '#spacing-tokens', icon: '📏', desc: 'Consistent spacing scale' },
    { title: 'Elevation Tokens', path: '#elevation-tokens', icon: '📦', desc: 'Shadow depth system' },
    { title: 'Border Radius Tokens', path: '#radius-tokens', icon: '⬜', desc: 'Border radius values' },
    { title: 'Breakpoints', path: '#breakpoint-tokens', icon: '📱', desc: 'Responsive breakpoint values' },
    { title: 'Buttons', path: '#component-buttons', icon: '🔘', desc: 'Button variants, sizes, and states' },
    { title: 'Cards', path: '#component-cards', icon: '🃏', desc: 'Card layouts and interactive cards' },
    { title: 'Badges', path: '#component-badges', icon: '🏷️', desc: 'Status badges and labels' },
    { title: 'Form Inputs', path: '#component-inputs', icon: '📝', desc: 'Input fields, validation states' },
    { title: 'Alerts', path: '#component-alerts', icon: '⚠️', desc: 'Contextual feedback messages' },
    { title: 'Modals', path: '#component-modals', icon: '🪟', desc: 'Dialog overlays and confirmations' },
    { title: 'Avatars', path: '#component-avatars', icon: '👤', desc: 'User avatars with initials' },
    { title: 'Tabs', path: '#component-tabs', icon: '📑', desc: 'Tab navigation panels' },
    { title: 'Tooltips', path: '#component-tooltips', icon: '💬', desc: 'Hover tooltip overlays' },
    { title: 'Progress Bars', path: '#component-progress', icon: '📊', desc: 'Progress indicators' },
    { title: 'Toggle Switch', path: '#component-toggles', icon: '🔀', desc: 'On/off toggle switches' },
    { title: 'Breadcrumbs', path: '#component-breadcrumbs', icon: '🍞', desc: 'Hierarchical navigation' },
    { title: 'Pagination', path: '#component-pagination', icon: '🔢', desc: 'Page navigation controls' },
    { title: 'Data Tables', path: '#component-tables', icon: '📋', desc: 'Structured data display' },
    { title: 'Skeletons', path: '#component-skeletons', icon: '💀', desc: 'Loading placeholder animations' },
    { title: 'Accordions', path: '#component-accordions', icon: '📨', desc: 'Collapsible content panels' },
    { title: 'Toast Notifications', path: '#component-toasts', icon: '🍞', desc: 'Brief feedback messages' },
    { title: 'React Integration', path: '#tab-react', icon: '⚛️', desc: 'React components and hooks' },
    { title: 'Vue Integration', path: '#tab-vue', icon: '💚', desc: 'Vue 3 composables and components' },
    { title: 'Vanilla JS Integration', path: '#tab-vanilla', icon: '🍦', desc: 'Framework-agnostic usage' },
    { title: 'Migration Guide', path: '#migration', icon: '🔄', desc: 'Version upgrade guides' }
  ];

  let searchSelectedIndex = 0;
  let searchFiltered = [];

  function openSearch() {
    searchModal.classList.add('active');
    searchModal.setAttribute('aria-hidden', 'false');
    searchInput.focus();
    document.body.style.overflow = 'hidden';
  }

  function closeSearch() {
    searchModal.classList.remove('active');
    searchModal.setAttribute('aria-hidden', 'true');
    searchInput.value = '';
    searchResults.innerHTML = '';
    document.body.style.overflow = '';
  }

  function runSearch(query) {
    const q = query.toLowerCase().trim();
    if (!q) {
      searchResults.innerHTML = '';
      searchFiltered = [];
      return;
    }
    searchFiltered = searchData.filter(item =>
      item.title.toLowerCase().includes(q) ||
      item.desc.toLowerCase().includes(q)
    );
    searchSelectedIndex = 0;
    renderSearchResults();
  }

  function renderSearchResults() {
    if (searchFiltered.length === 0) {
      searchResults.innerHTML = '<div style="padding: 16px; text-align: center; color: var(--text-muted); font-size: 14px;">No results found</div>';
      return;
    }
    searchResults.innerHTML = searchFiltered.map((item, i) => `
      <div class="search-result-item${i === searchSelectedIndex ? ' selected' : ''}" data-index="${i}" onclick="document.querySelector('${item.path}')?.scrollIntoView({behavior:'smooth'}); document.getElementById('search-modal').classList.remove('active');">
        <div class="search-result-icon">${item.icon}</div>
        <div class="search-result-content">
          <div class="search-result-title">${item.title}</div>
          <div class="search-result-path">${item.desc}</div>
        </div>
      </div>
    `).join('');
  }

  function moveSearchSelection(direction) {
    searchSelectedIndex = Math.max(0, Math.min(searchFiltered.length - 1, searchSelectedIndex + direction));
    const items = searchResults.querySelectorAll('.search-result-item');
    items.forEach((el, i) => {
      el.classList.toggle('selected', i === searchSelectedIndex);
    });
    if (items[searchSelectedIndex]) {
      items[searchSelectedIndex].scrollIntoView({ block: 'nearest' });
    }
  }

  function selectSearchItem() {
    if (searchFiltered[searchSelectedIndex]) {
      const item = searchFiltered[searchSelectedIndex];
      closeSearch();
      const target = document.querySelector(item.path);
      if (target) target.scrollIntoView({ behavior: 'smooth' });
    }
  }

  if (searchTrigger) searchTrigger.addEventListener('click', openSearch);
  document.querySelectorAll('[data-close-search]').forEach(el => {
    el.addEventListener('click', closeSearch);
  });
  if (searchInput) {
    searchInput.addEventListener('input', e => runSearch(e.target.value));
    searchInput.addEventListener('keydown', e => {
      if (e.key === 'ArrowDown') { e.preventDefault(); moveSearchSelection(1); }
      if (e.key === 'ArrowUp') { e.preventDefault(); moveSearchSelection(-1); }
      if (e.key === 'Enter') { e.preventDefault(); selectSearchItem(); }
      if (e.key === 'Escape') { closeSearch(); }
    });
  }

  // Global keyboard shortcut ⌘K / Ctrl+K
  document.addEventListener('keydown', e => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      if (searchModal.classList.contains('active')) {
        closeSearch();
      } else {
        openSearch();
      }
    }
    if (e.key === 'Escape' && searchModal.classList.contains('active')) {
      closeSearch();
    }
  });

  // ==========================================
  // Mobile Menu
  // ==========================================
  if (mobileMenuBtn) {
    mobileMenuBtn.addEventListener('click', () => {
      const nav = document.querySelector('.header-nav');
      if (nav.style.display === 'flex') {
        nav.style.display = '';
      } else {
        nav.style.display = 'flex';
        nav.style.position = 'absolute';
        nav.style.top = '100%';
        nav.style.left = '0';
        nav.style.right = '0';
        nav.style.background = 'var(--surface-elevated)';
        nav.style.flexDirection = 'column';
        nav.style.padding = 'var(--spacing-4)';
        nav.style.borderBottom = '1px solid var(--border-color)';
      }
    });
  }

  // ==========================================
  // Tabs
  // ==========================================
  function setupTabs(container) {
    if (!container) return;
    const tabs = container.querySelectorAll('[role="tab"]');
    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        tabs.forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');

        // For integration tabs, switch panels
        const panelId = tab.dataset.tab;
        if (panelId) {
          document.querySelectorAll('.tab-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `tab-${panelId}`);
          });
        }
      });
    });
  }

  // Setup all tab groups
  setupTabs(integrationTabList);
  // In-page component tabs (if any other tab groups)
  document.querySelectorAll('.tabs').forEach(tabsContainer => {
    setupTabs(tabsContainer);
  });

  // ==========================================
  // Accordion
  // ==========================================
  document.querySelectorAll('.accordion-trigger').forEach(trigger => {
    trigger.addEventListener('click', () => {
      const expanded = trigger.getAttribute('aria-expanded') === 'true';
      // Close all in this accordion
      const parent = trigger.closest('.accordion');
      if (parent) {
        parent.querySelectorAll('.accordion-trigger').forEach(t => {
          t.setAttribute('aria-expanded', 'false');
        });
      }
      trigger.setAttribute('aria-expanded', String(!expanded));
    });
  });

  // ==========================================
  // Toast Notifications
  // ==========================================
  window.showToast = function (type, message) {
    const container = document.getElementById('toast-container');
    if (!container) return;

    const icons = {
      success: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
      error: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
      info: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
      ${icons[type] || ''}
      <div>${message}</div>
      <button class="toast-close" aria-label="Dismiss notification">&times;</button>
    `;

    container.appendChild(toast);

    const removeToast = () => {
      toast.style.animation = 'toast-slide-in 0.3s ease reverse';
      setTimeout(() => toast.remove(), 300);
    };

    toast.querySelector('.toast-close').addEventListener('click', removeToast);
    setTimeout(removeToast, 4000);
  };

  // ==========================================
  // Token Rendering from JSON
  // ==========================================
  function renderTokens() {
    fetch('src/data/tokens.json')
      .then(r => r.json())
      .then(data => {
        renderColorTokens(data.tokens.color);
        renderFontFamilyTokens(data.tokens.typography.fontFamily);
        renderFontSizeTokens(data.tokens.typography.fontSize);
        renderFontWeightTokens(data.tokens.typography.fontWeight);
        renderSpacingTokens(data.tokens.spacing);
        renderElevationTokens(data.tokens.elevation);
        renderRadiusTokens(data.tokens.borderRadius);
        renderBreakpointTokens(data.tokens.breakpoints);
      })
      .catch(() => {
        // Fallback: tokens already in CSS, nothing to do
      });
  }

  function renderColorTokens(color) {
    const grid = document.getElementById('color-grid');
    if (!grid) return;
    const groups = { ...color.brand, ...color.neutral, ...color.semantic };
    grid.innerHTML = Object.entries(groups).map(([name, token]) => `
      <div class="color-token">
        <div class="color-swatch" style="background: ${token.value}; border: 1px solid var(--border-color);"></div>
        <div class="color-info">
          <div class="color-name">${name}</div>
          <div class="color-value">${token.value}</div>
          <div class="color-desc">${token.description}</div>
        </div>
      </div>
    `).join('');
  }

  function renderFontFamilyTokens(fontFamily) {
    const list = document.getElementById('font-family-list');
    if (!list) return;
    const previews = { sans: 'token-preview-sans', mono: 'token-preview-mono', display: 'token-preview-sans' };
    list.innerHTML = Object.entries(fontFamily).map(([name, token]) => `
      <div class="token-list-item">
        <span class="${previews[name] || ''}">${name}</span>
        <code>${token.value}</code>
      </div>
    `).join('');
  }

  function renderFontSizeTokens(fontSize) {
    const list = document.getElementById('font-size-list');
    if (!list) return;
    list.innerHTML = Object.entries(fontSize).map(([name, token]) => `
      <div class="token-list-item">
        <span style="font-size: ${token.value};">${name}</span>
        <code>${token.value}</code>
      </div>
    `).join('');
  }

  function renderFontWeightTokens(fontWeight) {
    const list = document.getElementById('font-weight-list');
    if (!list) return;
    list.innerHTML = Object.entries(fontWeight).map(([name, token]) => `
      <div class="token-list-item">
        <span style="font-weight: ${token.value};">${name}</span>
        <code>${token.value}</code>
      </div>
    `).join('');
  }

  function renderSpacingTokens(spacing) {
    const visual = document.getElementById('spacing-visual');
    if (!visual) return;
    visual.innerHTML = Object.entries(spacing).map(([name, token]) => {
      const px = parseFloat(token.value) * 16; // rem to px approximation
      return `
        <div class="spacing-item">
          <span class="spacing-label">${name} <code style="font-size:var(--font-size-xs);color:var(--text-muted)">${token.value}</code></span>
          <div class="spacing-bar" style="width: ${Math.max(px, 4)}px;"></div>
        </div>
      `;
    }).join('');
  }

  function renderElevationTokens(elevation) {
    const grid = document.getElementById('elevation-grid');
    if (!grid) return;
    grid.innerHTML = Object.entries(elevation).map(([name, token]) => `
      <div class="elevation-item">
        <div class="elevation-demo" style="box-shadow: ${token.value === 'none' ? 'none' : token.value};"></div>
        <div class="elevation-label">${name}</div>
      </div>
    `).join('');
  }

  function renderRadiusTokens(radius) {
    const grid = document.getElementById('radius-grid');
    if (!grid) return;
    grid.innerHTML = Object.entries(radius).map(([name, token]) => `
      <div class="radius-item">
        <div class="radius-demo" style="border-radius: ${token.value};"></div>
        <div class="radius-label">${name} <code style="font-size:var(--font-size-xs);color:var(--text-muted)">${token.value}</code></div>
      </div>
    `).join('');
  }

  function renderBreakpointTokens(breakpoints) {
    const table = document.getElementById('breakpoint-table');
    if (!table) return;
    const usage = {
      sm: 'Large phones',
      md: 'Tablets',
      lg: 'Laptops',
      xl: 'Desktops',
      '2xl': 'Large monitors'
    };
    table.innerHTML = Object.entries(breakpoints).map(([name, token]) => `
      <tr>
        <td><code>${name}</code></td>
        <td><code>${token.value}</code></td>
        <td>${usage[name] || token.description}</td>
      </tr>
    `).join('');
  }

  // ==========================================
  // Scroll Reveal Animation
  // ==========================================
  function setupScrollReveal() {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.style.opacity = '1';
          entry.target.style.transform = 'translateY(0)';
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -50px 0px' });

    document.querySelectorAll('.token-group, .component-block, .changelog-item, .migration-guide').forEach(el => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(20px)';
      el.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
      observer.observe(el);
    });
  }

  // ==========================================
  // Smooth scroll for anchor links
  // ==========================================
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const href = link.getAttribute('href');
      if (href === '#') return;
      const target = document.querySelector(href);
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth' });
        // Close mobile menu if open
        const nav = document.querySelector('.header-nav');
        if (nav && nav.style.display === 'flex') {
          nav.style.display = '';
        }
      }
    });
  });

  // ==========================================
  // Initialize
  // ==========================================
  document.addEventListener('DOMContentLoaded', () => {
    renderTokens();
    setupScrollReveal();
  });

})();
