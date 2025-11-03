
(() => {
  const sidebar = document.getElementById('sidebar');
  const toggleBtn = document.getElementById('toggleSidebar');

  if (!sidebar) return; // fail gracefully if page doesn't have a sidebar

  const isMobile = () => window.matchMedia('(max-width: 768px)').matches;

  function ensureOverlay() {
    let ov = document.getElementById('sidebar-overlay');
    if (!ov) {
      ov = document.createElement('div');
      ov.id = 'sidebar-overlay';
      ov.className = 'fixed inset-0 bg-black bg-opacity-30 z-30 hidden md:hidden';
      document.body.appendChild(ov);
      ov.addEventListener('click', closeSidebar);
    }
    return ov;
  }

  function openSidebar() {
    sidebar.classList.remove('-translate-x-full');
    document.body.classList.add('overflow-hidden');
    if (isMobile()) {
      const ov = ensureOverlay();
      ov.classList.remove('hidden');
    }
  }

  function closeSidebar() {
    sidebar.classList.add('-translate-x-full');
    document.body.classList.remove('overflow-hidden');
    const ov = document.getElementById('sidebar-overlay');
    if (ov) ov.classList.add('hidden');
  }

  function toggleSidebar() {
    if (sidebar.classList.contains('-translate-x-full')) openSidebar();
    else closeSidebar();
  }

  // Initial state by viewport
  function applyInitial() {
    if (isMobile()) {
      sidebar.classList.add('-translate-x-full');
      const ov = document.getElementById('sidebar-overlay');
      if (ov) ov.classList.add('hidden');
    } else {
      sidebar.classList.remove('-translate-x-full');
      const ov = document.getElementById('sidebar-overlay');
      if (ov) ov.classList.add('hidden');
    }
  }

  // Attach handlers
  toggleBtn?.addEventListener('click', (e) => {
    e.stopPropagation();
    toggleSidebar();
  });

  // Close on click outside (mobile)
  document.addEventListener('click', (e) => {
    if (!isMobile()) return;
    const target = e.target;
    if (!sidebar.contains(target) && !toggleBtn?.contains(target)) {
      closeSidebar();
    }
  });

  // Close on ESC
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeSidebar();
  });

  // Auto-close after nav click on mobile
  sidebar.querySelectorAll('a').forEach((a) =>
    a.addEventListener('click', () => {
      if (isMobile()) closeSidebar();
    })
  );

  // Expose loader helpers globally (used by pages)
  window.showLoader = () => document.getElementById('loader')?.classList.remove('hidden');
  window.hideLoader = () => document.getElementById('loader')?.classList.add('hidden');

  // Apply now + on resize
  applyInitial();
  window.addEventListener('resize', applyInitial);
})();
