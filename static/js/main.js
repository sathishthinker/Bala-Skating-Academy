// Bala Skating Academy – Main JS

document.addEventListener('DOMContentLoaded', function () {

  // ── AOS init ──────────────────────────────────────────────
  if (typeof AOS !== 'undefined') {
    AOS.init({ duration: 700, once: true, offset: 60 });
  }

  // ── Navbar scroll effect ──────────────────────────────────
  const nav = document.getElementById('mainNav');
  if (nav) {
    const onScroll = () => {
      nav.classList.toggle('scrolled', window.scrollY > 50);
    };
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
  }

  // ── Smooth scroll for hero anchor ────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(link => {
    link.addEventListener('click', function (e) {
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        e.preventDefault();
        target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  });

  // ── Counter animation for hero stats ─────────────────────
  const counters = document.querySelectorAll('.stat-num');
  if (counters.length) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const el = entry.target;
          const raw = el.textContent.trim();
          const num = parseInt(raw.replace(/\D/g, ''), 10);
          if (!isNaN(num) && num > 0) {
            animateCounter(el, num, raw);
          }
          observer.unobserve(el);
        }
      });
    }, { threshold: 0.5 });
    counters.forEach(c => observer.observe(c));
  }

  function animateCounter(el, target, raw) {
    const suffix = raw.replace(/[\d,]/g, '');
    const duration = 1400;
    const start = performance.now();
    const step = (ts) => {
      const progress = Math.min((ts - start) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      el.textContent = Math.floor(eased * target) + suffix;
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  // ── Active nav link on scroll (single-page sections) ─────
  // (multi-page site — handled via Jinja template class)

  // ── Form validation feedback ──────────────────────────────
  const forms = document.querySelectorAll('form[novalidate]');
  forms.forEach(form => {
    form.addEventListener('submit', function (e) {
      if (!form.checkValidity()) {
        e.preventDefault();
        e.stopPropagation();
      }
      form.classList.add('was-validated');
    });
  });

  // ── Auto-dismiss alerts ───────────────────────────────────
  document.querySelectorAll('.alert:not(.alert-permanent)').forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 5000);
  });

});
