const toggleButton = document.getElementById('toggle-btn')
const sidebar = document.getElementById('sidebar')

function toggleSidebar(){
  sidebar.classList.toggle('close')
  toggleButton.classList.toggle('rotate')

  closeAllSubMenus()
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

function toggleSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.toggle('close');
  // Save state
  localStorage.setItem('sidebar-closed', sidebar.classList.contains('close'));
}

// Restore sidebar state on page load
document.addEventListener('DOMContentLoaded', function() {
  const sidebar = document.getElementById('sidebar');
  if (localStorage.getItem('sidebar-closed') === 'true') {
    sidebar.classList.add('close');
  } else {
    sidebar.classList.remove('close');
  }
});