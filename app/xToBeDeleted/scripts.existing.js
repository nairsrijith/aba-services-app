function toggleSidebar() {
  document.getElementById("sidebar").classList.toggle("collapsed");
}

function toggleMobileMenu() {
  document.getElementById("mobileMenu").classList.toggle("show");
}

document.addEventListener('DOMContentLoaded', function() {
    var sidebar = document.getElementById('sidebar');
    if (sidebar) {
      sidebar.classList.add('notransition');
      if (localStorage.getItem('sidebar-collapsed') === 'true') {
        sidebar.classList.add('collapsed');
        document.body.classList.add('sidebar-collapsed-mode');
      }
      setTimeout(function() {
        sidebar.classList.remove('notransition');
      }, 50);
    }

    window.toggleSidebar = function() {
        sidebar.classList.toggle('collapsed');
        document.body.classList.toggle('sidebar-collapsed-mode');
        localStorage.setItem('sidebar-collapsed', sidebar.classList.contains('collapsed'));
    };
});