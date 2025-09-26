const toggleButton = document.getElementById('toggle-btn')
const sidebar = document.getElementById('sidebar')


function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  const toggleButton = document.getElementById('toggle-btn');
  sidebar.classList.toggle('close');
  toggleButton.classList.toggle('rotated');
  closeAllSubMenus();
  // Save state
  localStorage.setItem('sidebar-closed', sidebar.classList.contains('close'));
}

function toggleSubMenu(button){

  if(!button.nextElementSibling.classList.contains('show')){
    closeAllSubMenus()
  }

  button.nextElementSibling.classList.toggle('show')
  button.classList.toggle('rotate')

  if(sidebar.classList.contains('close')){
    sidebar.classList.toggle('close')
    toggleButton.classList.toggle('rotate')
  }
}

function closeAllSubMenus(){
  Array.from(sidebar.getElementsByClassName('show')).forEach(ul => {
    ul.classList.remove('show')
    ul.previousElementSibling.classList.remove('rotate')
  })
}

document.addEventListener('DOMContentLoaded', function() {
  var toastElList = [].slice.call(document.querySelectorAll('.toast'));
  toastElList.forEach(function(toastEl) {
    var toast = new bootstrap.Toast(toastEl);
    toast.show();
  });
});



// Restore sidebar state on page load
document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  const toggleButton = document.getElementById('toggle-btn');
  if (localStorage.getItem('sidebar-closed') === 'true') {
    sidebar.classList.add('close');
    toggleButton.classList.add('rotated');
  } else {
    sidebar.classList.remove('close');
    toggleButton.classList.remove('rotated');
  }

  // Close submenus when mouse leaves sidebar
  sidebar.addEventListener('mouseleave', function() {
    closeAllSubMenus();
  });
});

window.addEventListener('resize', function() {
  const sidebar = document.getElementById('sidebar');
  const toggleButton = document.getElementById('toggle-btn');
  if (window.innerWidth <= 800) {
    sidebar.classList.remove('close');
    if (toggleButton) toggleButton.classList.remove('rotated');
  }
});