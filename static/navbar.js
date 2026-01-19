/**
 * Railway Visualization System - Navigation Sidebar JS
 * Controls sidebar behavior and responsiveness
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM element references
    const sidebarCollapse = document.getElementById('sidebarCollapse');
    const sidebar = document.querySelector('.sidebar');
    const contentWrapper = document.querySelector('.content-wrapper');
    const overlay = document.getElementById('overlay');
    const currentPath = window.location.pathname;
    const themeToggle = document.getElementById('themeToggle');
    
    // Toggle sidebar on button click
    if (sidebarCollapse) {
        sidebarCollapse.addEventListener('click', toggleSidebar);
    }
    
    // Close sidebar when clicking overlay (mobile view)
    if (overlay) {
        overlay.addEventListener('click', closeSidebar);
    }
    
    // Theme toggle functionality
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
        
        // Set initial theme state based on localStorage or user preference
        setInitialTheme();
    }
    
    // Handle window resize events
    window.addEventListener('resize', handleResize);
    
    // Highlight current page in navigation
    highlightCurrentPage();
    
    /**
     * Toggle sidebar visibility
     */
    function toggleSidebar() {
        sidebar.classList.toggle('active');
        contentWrapper.classList.toggle('active');
        overlay.classList.toggle('active');
    }
    
    /**
     * Close sidebar and overlay
     */
    function closeSidebar() {
        sidebar.classList.remove('active');
        contentWrapper.classList.remove('active');
        overlay.classList.remove('active');
    }
    
    /**
     * Handle responsive behavior on window resize
     */
    function handleResize() {
        if (window.innerWidth > 768) {
            closeSidebar();
        }
    }
    
    /**
     * Highlight the current page in the navigation menu
     */
    function highlightCurrentPage() {
        const navLinks = document.querySelectorAll('.sidebar ul li a');
        
        navLinks.forEach(link => {
            const linkPath = link.getAttribute('href');
            
            if ((currentPath.includes(linkPath) && linkPath !== '/') || 
                (currentPath === '/' && linkPath === '/')) {
                link.parentElement.classList.add('active');
            }
        });
    }
    
    /**
     * Toggle between light and dark theme
     */
    function toggleTheme() {
        if (document.body.classList.contains('dark-theme')) {
            document.body.classList.remove('dark-theme');
            localStorage.setItem('theme', 'light');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            themeToggle.title = 'Switch to dark theme';
        } else {
            document.body.classList.add('dark-theme');
            localStorage.setItem('theme', 'dark');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            themeToggle.title = 'Switch to light theme';
        }
    }
    
    /**
     * Set initial theme based on localStorage or user preference
     */
    function setInitialTheme() {
        // Check if theme preference is stored in localStorage
        const savedTheme = localStorage.getItem('theme');
        
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
            themeToggle.title = 'Switch to light theme';
        } else if (savedTheme === 'light') {
            document.body.classList.remove('dark-theme');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
            themeToggle.title = 'Switch to dark theme';
        } else {
            // Check for OS preference if no saved theme
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                document.body.classList.add('dark-theme');
                themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
                themeToggle.title = 'Switch to light theme';
                localStorage.setItem('theme', 'dark');
            } else {
                // Default to light theme
                document.body.classList.remove('dark-theme');
                themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
                themeToggle.title = 'Switch to dark theme';
                localStorage.setItem('theme', 'light');
            }
        }
    }
});
