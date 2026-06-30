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

//==========================================
// DYNAMIC ACTIVE NAV HIGHLIGHTING
// Automatically highlights the current page
// in both desktop and mobile navigation.
//==========================================
function highlightActiveNav() {
  var pagePath = decodeURIComponent(window.location.pathname);
  if (pagePath.charAt(0) === '/') pagePath = pagePath.substring(1);

  // Resolve a possibly-relative href against the current page path.
  // Handles both web server paths (index.html) and
  // file:// protocol paths (C:/Users/.../index.html).
  function resolve(href) {
    // Treat the current page's directory as the base
    var parts = pagePath.split('/');
    parts.pop(); // remove current filename
    // Walk through each segment of the href
    var segs = href.split('/');
    for (var i = 0; i < segs.length; i++) {
      if (segs[i] === '..') { if (parts.length) parts.pop(); }
      else { parts.push(decodeURIComponent(segs[i])); }
    }
    return parts.join('/');
  }

  function matches(target) {
    var resolved = resolve(target);
    if (pagePath === resolved) return true;
    var dir = resolved.replace(/\.html$/, '') + '/';
    if (pagePath.indexOf(dir) === 0) return true;
    return false;
  }

  // Desktop topnav
  var nav = document.getElementById('myTopnav');
  if (nav) {
    var links = nav.querySelectorAll('a');
    for (var i = 0; i < links.length; i++) {
      var href = links[i].getAttribute('href');
      if (href && href !== 'javascript:void(0);') {
        links[i].classList.remove('active');
        if (matches(href)) links[i].classList.add('active');
      }
    }
  }

  // Mobile bottom nav
  var navBtns = document.querySelectorAll('.mobile-nav-btn');
  for (var i = 0; i < navBtns.length; i++) {
    var dataHref = navBtns[i].getAttribute('data-href');
    navBtns[i].classList.remove('active');
    if (dataHref && matches(dataHref)) navBtns[i].classList.add('active');
  }
}
highlightActiveNav();

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



