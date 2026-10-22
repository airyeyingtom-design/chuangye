(() => {
  const progress = document.getElementById("progress");
  const topnav = document.getElementById("topnav");

  const onScroll = () => {
    const max = document.documentElement.scrollHeight - window.innerHeight;
    const p = max > 0 ? window.scrollY / max : 0;
    if (progress) progress.style.width = `${Math.min(1, Math.max(0, p)) * 100}%`;
    if (topnav) topnav.classList.toggle("solid", window.scrollY > 40);

    document.querySelectorAll("[data-parallax] img").forEach((img) => {
      const host = img.closest("[data-parallax]");
      if (!host) return;
      const rect = host.getBoundingClientRect();
      const view = window.innerHeight + rect.height;
      const ratio = (window.innerHeight - rect.top) / view;
      const y = (ratio - 0.5) * 36;
      img.style.transform = `scale(1.12) translate3d(0, ${y.toFixed(2)}px, 0)`;
    });
  };

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-in");
          io.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.18, rootMargin: "0px 0px -8% 0px" }
  );
  document.querySelectorAll(".reveal, .reveal-clip").forEach((el) => io.observe(el));

  document.querySelectorAll("[data-go]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sel = btn.getAttribute("data-go");
      const el = sel && document.querySelector(sel);
      if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });

  let ticking = false;
  window.addEventListener(
    "scroll",
    () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        onScroll();
        ticking = false;
      });
    },
    { passive: true }
  );
  onScroll();

  // gentle auto-nudge for horizontal pair on first view
  const pair = document.getElementById("pair");
  if (pair) {
    const pairIo = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          pair.scrollTo({ left: 36, behavior: "smooth" });
          setTimeout(() => pair.scrollTo({ left: 0, behavior: "smooth" }), 700);
          pairIo.disconnect();
        });
      },
      { threshold: 0.45 }
    );
    pairIo.observe(pair);
  }
})();
