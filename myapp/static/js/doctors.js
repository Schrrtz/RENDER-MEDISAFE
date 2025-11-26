// Extracted JS from doctors.php
function show(tab){
  document.querySelectorAll('[data-tab]').forEach(s=>s.style.display='none');
  document.getElementById(tab).style.display='block';
  document.querySelectorAll('.nav a').forEach(a=>a.classList.remove('active'));
  var link=document.querySelector('.nav a[href="#'+tab+'"]');
  if(link){link.classList.add('active');}
  window.location.hash = tab;
}

function toggleMenu(){
  var n=document.querySelector('.nav');
  if(n){ n.classList.toggle('show'); }
}

// Profile dropdown state management
var profileDropdownState=false;

function toggleProfileMenu(e){
  if(e){e.stopPropagation();e.preventDefault();}
  var d=document.getElementById('profileDropdown');
  var c=document.getElementById('caretIcon');
  if(!d){return false;}
  
  // Toggle state
  profileDropdownState=!profileDropdownState;
  
  if(profileDropdownState){
    // Show dropdown
    d.style.display='flex';
    d.style.visibility='visible';
    d.style.opacity='1';
    d.style.pointerEvents='auto';
    d.style.zIndex='1000';
    if(d.style.flexDirection!=='column'){d.style.flexDirection='column';}
    if(c){c.style.transform='rotate(180deg)';}
  }else{
    // Hide dropdown
    d.style.display='none';
    d.style.visibility='hidden';
    d.style.opacity='0';
    d.style.pointerEvents='none';
    if(c){c.style.transform='rotate(0deg)';}
  }
  return false;
}

// Close dropdown function - can be called from anywhere
function closeProfileDropdown(){
  var d=document.getElementById('profileDropdown');
  var c=document.getElementById('caretIcon');
  if(d){
    profileDropdownState=false;
    d.style.display='none';
    d.style.visibility='hidden';
    d.style.opacity='0';
    d.style.pointerEvents='none';
  }
  if(c){c.style.transform='rotate(0deg)';}
}

// Close dropdown when clicking outside
document.addEventListener('click',function(e){
  var btn=document.getElementById('userMenuBtn');
  var dd=document.getElementById('profileDropdown');
  var modal=document.getElementById('profileSettingsModal');
  var quickModal=document.getElementById('quickProfileModal');
  
  // Don't close if clicking on button, dropdown, or modals
  if(dd && e.target && 
     !dd.contains(e.target) && 
     !btn.contains(e.target) && 
     (!modal || !modal.contains(e.target)) &&
     (!quickModal || !quickModal.contains(e.target))){
    closeProfileDropdown();
  }
});

// Initialize dropdown state on page load
document.addEventListener('DOMContentLoaded',function(){
  var d=document.getElementById('profileDropdown');
  if(d){
    closeProfileDropdown();
  }
  
  // Handle hash navigation
  var hash = window.location.hash.replace('#','');
  if(hash && document.getElementById(hash)) {
    show(hash);
  } else {
    show('dashboard');
  }
});

// Close dropdown on Escape key
document.addEventListener('keydown',function(e){
  if(e.key==='Escape'){
    var dd=document.getElementById('profileDropdown');
    var modal=document.getElementById('profileSettingsModal');
    var quickModal=document.getElementById('quickProfileModal');
    
    // Close dropdown if open
    if(dd && profileDropdownState){
      closeProfileDropdown();
    }
    
    // Close modals if open
    if(modal && modal.style.display==='flex'){
      if(typeof closeProfileSettings === 'function'){
        closeProfileSettings();
      }
    }
    if(quickModal && quickModal.style.display==='flex'){
      if(typeof closeQuickProfile === 'function'){
        closeQuickProfile();
      }
    }
  }
});

