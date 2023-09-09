document.addEventListener("DOMContentLoaded", function() {
  document.getElementById("startMediation").addEventListener("click", function(){
    location.href='/analyse_conflict_private';
  });
  document.getElementById("skipPrivateMediation").addEventListener("click", function(){
    location.href='/public_mediation';
  });
});