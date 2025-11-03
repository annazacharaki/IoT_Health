
document.addEventListener('DOMContentLoaded', function () {
  const sidebar = document.getElementById('sidebar');
  const main = document.getElementById('main');
  const btn = document.getElementById('toggleSidebar');

  if (!sidebar || !btn) return;

  const MOBILE = 768;
  const isMobile = () => window.innerWidth < MOBILE;

  // Create (once) a click-to-close overlay for mobile
  let overlay = document.getElementById('sidebar-overlay');
  if (!overlay) {
    overlay = document.createElement('div');
    overlay.id = 'sidebar-overlay';
    overlay.style.position = 'fixed';
    overlay.style.inset = '0';
    overlay.style.background = 'rgba(0,0,0,.35)';
    overlay.style.zIndex = '30';
    overlay.style.display = 'none';
    document.body.appendChild(overlay);
    overlay.addEventListener('click', closeSidebar);
  }

  function openSidebar() {
    sidebar.classList.remove('-translate-x-full');
    if (isMobile()) overlay.style.display = 'block';
  }
  function closeSidebar() {
    sidebar.classList.add('-translate-x-full');
    overlay.style.display = 'none';
  }
  function toggleSidebar() {
    if (sidebar.classList.contains('-translate-x-full')) openSidebar();
    else closeSidebar();
  }

  function applyResponsiveLayout() {
    if (isMobile()) {
      // Mobile: hide sidebar by default and remove desktop spacing
      sidebar.classList.add('-translate-x-full');
      document.body.classList.remove('with-sidebar-desktop');
      overlay.style.display = 'none';
    } else {
      // Desktop: show sidebar and add spacing for content (no overlay)
      sidebar.classList.remove('-translate-x-full');
      document.body.classList.add('with-sidebar-desktop');
      overlay.style.display = 'none';
    }
  }

  // Hook up interactions
  btn.addEventListener('click', function (e) {
    e.stopPropagation();
    toggleSidebar();
  });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
  });
  document.addEventListener('click', (e) => {
    if (!isMobile()) return;
    const t = e.target;
    if (!sidebar.contains(t) && !btn.contains(t)) closeSidebar();
  });
  // Auto-close after clicking a link (mobile UX)
  sidebar.querySelectorAll('a').forEach(a => {
    a.addEventListener('click', () => { if (isMobile()) closeSidebar(); });
  });

  // Initial + on resize
  applyResponsiveLayout();
  window.addEventListener('resize', applyResponsiveLayout);

  // Keep public helpers as you already used them
  window.showLoader = function () {
    const l = document.getElementById('loader');
    if (l) l.classList.remove('hidden');
  };
  window.hideLoader = function () {
    const l = document.getElementById('loader');
    if (l) l.classList.add('hidden');
  };
});
