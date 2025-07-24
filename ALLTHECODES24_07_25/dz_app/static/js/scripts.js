document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main');
    const toggleButton = document.getElementById('toggleSidebar');

    function usesTransform() {
        return sidebar.className.includes('translate-x');
    }

    function isSidebarOpen() {
        if (usesTransform()) {
            return !sidebar.classList.contains('-translate-x-full');
        }
        return window.getComputedStyle(sidebar).width !== '0px';
    }

    function openSidebar() {
        if (usesTransform()) {
            sidebar.classList.remove('-translate-x-full');
        } else {
            sidebar.style.width = '250px';
            if (mainContent) mainContent.style.marginLeft = '250px';
        }
    }

    function closeSidebar() {
        if (usesTransform()) {
            sidebar.classList.add('-translate-x-full');
        } else {
            sidebar.style.width = '0';
            if (mainContent) mainContent.style.marginLeft = '0';
        }
    }

    function toggleSidebar() {
        if (isSidebarOpen()) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }

    window.toggleSidebar = toggleSidebar;

    toggleButton.addEventListener('click', toggleSidebar);
	

    // Close sidebar when a sidebar link is clicked
    sidebar.querySelectorAll('a').forEach(function(link) {
        link.addEventListener('click', toggleSidebar);
    });

    // Close sidebar when clicking outside
    document.addEventListener('click', function(event) {
        if (!sidebar.contains(event.target) && !toggleButton.contains(event.target) && isSidebarOpen()) {
            closeSidebar();
        }
    });
});


function showLoader() {
  document.getElementById('loader').classList.remove('hidden');
}

function hideLoader() {
  document.getElementById('loader').classList.add('hidden');
} 


