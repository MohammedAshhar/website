//SPLASH SCREEN
window.addEventListener('load', function() {
var splash = document.getElementById('splash');
if (splash) {
var duration = splash.getAttribute('data-duration');
if (!duration) duration = 500;
setTimeout(function() {
splash.classList.add('fade-out');
setTimeout(function() { splash.style.display = 'none'; }, 500);
}, parseInt(duration));
}
});

//NAVIGATION
function myFunction() {
var x = document.getElementById("myTopnav");
if (x.className === "topnav") {
x.className += " responsive";
} else {
x.className = "topnav";
}
}



//==========================================
// MOBILE BOTTOM NAV - Active Pill Slider
//==========================================
// Positions a rounded pill behind whichever
// nav button is active, with a springy
// Apple-style animation. Also handles
// navigation when a button is tapped.
//==========================================
(function() {

  // Grab the nav buttons and the pill element
  var navBtns = document.querySelectorAll('.mobile-nav-btn');
  var activePill = document.getElementById('mobileActivePill');

  // If the bottom nav doesn't exist on this
  // page (e.g. someone removed it), just bail.
  if (!navBtns.length || !activePill) return;

  //------------------------
  // Position the pill
  //------------------------
  function updatePill(btn, smooth) {
    if (!btn) return;
    if (!smooth) {
      activePill.style.transition = 'none';
    } else {
      activePill.style.transition =
        'transform 0.5s cubic-bezier(0.34, 1.2, 0.64, 1), ' +
        'width 0.5s cubic-bezier(0.34, 1.2, 0.64, 1)';
    }
    activePill.style.width  = btn.offsetWidth + 'px';
    activePill.style.transform = 'translateX(' + btn.offsetLeft + 'px)';
  }

  // Initial pill position
  var activeBtn = document.querySelector('.mobile-nav-btn.active');
  if (activeBtn) {
    setTimeout(function() {
      updatePill(activeBtn, false);
    }, 50);
  }

  // Navigate on tap
  for (var i = 0; i < navBtns.length; i++) {
    (function(btn) {
      btn.addEventListener('click', function() {
        var href = btn.getAttribute('data-href');
        if (href) {
          window.location.href = href;
        }
      });
    })(navBtns[i]);
  }

  // Reposition on resize
  window.addEventListener('resize', function() {
    var active = document.querySelector('.mobile-nav-btn.active');
    if (active) updatePill(active, false);
  });

})();


//MODAL
function openModal() {
document.getElementById("myModal").style.display = "block";
}

function closeModal() {
document.getElementById("myModal").style.display = "none";
}

document.addEventListener('keydown', function(e) {
if (e.key === 'Escape') {
var m = document.getElementById('myModal');
if (m && m.style.display === 'block') closeModal();
}
});

var slideIndex = 1;
showSlides(slideIndex);

function plusSlides(n) {
showSlides(slideIndex += n);
}

function currentSlide(n) {
showSlides(slideIndex = n);
}

function showSlides(n) {
var i;
var slides = document.getElementsByClassName("mySlides");
var dots = document.getElementsByClassName("demo");
var captionText = document.getElementById("caption");
if (n > slides.length) {slideIndex = 1}
if (n < 1) {slideIndex = slides.length}
for (i = 0; i < slides.length; i++) {
  slides[i].style.display = "none";
}
for (i = 0; i < dots.length; i++) {
  dots[i].className = dots[i].className.replace(" active", "");
}
slides[slideIndex-1].style.display = "block";
dots[slideIndex-1].className += " active";
captionText.innerHTML = dots[slideIndex-1].alt;
}
