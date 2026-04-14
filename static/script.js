document.addEventListener('DOMContentLoaded', () => {
  // Nav toggle (mobile)
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');
  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('open');
    });
  }

  // Login button in header
  const loginBtn = document.getElementById('loginBtn');
  if (loginBtn) {
    loginBtn.addEventListener('click', () => {
      window.location.href = '/login/';
    });
  }

  // Signup button in header
  const signupBtn = document.getElementById('signupBtn');
  if (signupBtn) {
    signupBtn.addEventListener('click', () => {
      window.location.href = '/signup/';
    });
  }

  // "More Info" toggle on property cards
  document.querySelectorAll('.info-toggle').forEach((btn) => {
    btn.addEventListener('click', () => {
      const more = btn.parentElement.querySelector('.more-info');
      if (!more) return;
      const visible = more.style.display !== 'none';
      more.style.display = visible ? 'none' : 'block';
      btn.textContent = visible ? 'More Info' : 'Hide Info';
    });
  });

  // Chatbot widget has been migrated to a Django partial (templates/partials/chatbot.html).
});

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      // Does this cookie string begin with the name we want?
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}


