document.addEventListener('DOMContentLoaded', function() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.getElementById('main');
    const toggleSidebar = document.getElementById('toggleSidebar');

toggleSidebar.addEventListener('click', function() {
    const currentWidth = window.getComputedStyle(sidebar).width;
    if (currentWidth === '250px') {
        sidebar.style.width = '0';
        mainContent.style.marginLeft = '0';
    } else {
        sidebar.style.width = '250px';
        mainContent.style.marginLeft = '250px';
    }
});

    // Close sidebar when clicking outside
    document.addEventListener('click', function(event) {
        if (!sidebar.contains(event.target) && !toggleSidebar.contains(event.target) && sidebar.style.width === '250px') {
            sidebar.style.width = '0';
            mainContent.style.marginLeft = '0';
        }
    });
});