const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

const topbar = document.querySelector(".topbar");
const revealItems = document.querySelectorAll(".reveal");
const counters = document.querySelectorAll("[data-count]");
const heroScene = document.querySelector("#heroScene");
const year = document.querySelector("#year");
const progressBar = document.querySelector(".reading-progress span");

if (year) {
  year.textContent = new Date().getFullYear();
}

const setTopbarState = () => {
  if (!topbar) return;
  topbar.classList.toggle("is-scrolled", window.scrollY > 10);
};

setTopbarState();
window.addEventListener("scroll", setTopbarState, { passive: true });

if (revealItems.length) {
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.16 }
  );

  revealItems.forEach((item) => revealObserver.observe(item));
}

if (counters.length && !prefersReducedMotion) {
  const animateCount = (element) => {
    const target = Number(element.dataset.count || 0);
    const duration = 1200;
    const startTime = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      element.textContent = String(Math.floor(target * eased));
      if (progress < 1) {
        requestAnimationFrame(tick);
      } else {
        element.textContent = String(target);
      }
    };

    requestAnimationFrame(tick);
  };

  const countObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          animateCount(entry.target);
          countObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.7 }
  );

  counters.forEach((counter) => countObserver.observe(counter));
}

if (heroScene && !prefersReducedMotion) {
  heroScene.addEventListener("pointermove", (event) => {
    const rect = heroScene.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width - 0.5) * 14;
    const y = ((event.clientY - rect.top) / rect.height - 0.5) * 14;
    heroScene.style.setProperty("--pointer-x", x.toFixed(2));
    heroScene.style.setProperty("--pointer-y", y.toFixed(2));
  });

  heroScene.addEventListener("pointerleave", () => {
    heroScene.style.setProperty("--pointer-x", "0");
    heroScene.style.setProperty("--pointer-y", "0");
  });
}

const syncProgressBar = () => {
  if (!progressBar) return;
  const scrollable = document.documentElement.scrollHeight - window.innerHeight;
  const progress = scrollable > 0 ? window.scrollY / scrollable : 0;
  progressBar.style.transform = `scaleX(${Math.min(Math.max(progress, 0), 1)})`;
};

if (progressBar) {
  syncProgressBar();
  window.addEventListener("scroll", syncProgressBar, { passive: true });
  window.addEventListener("resize", syncProgressBar);
}
