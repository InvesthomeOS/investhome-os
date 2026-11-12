export function lockPageScroll() {
  if (typeof document === 'undefined') return () => {};
  const html = document.documentElement;
  const body = document.body;
  const previous = {
    htmlOverflow: html.style.overflow,
    bodyOverflow: body.style.overflow,
  };
  html.classList.add('ih-scroll-lock');
  html.style.overflow = 'hidden';
  body.style.overflow = 'hidden';
  return () => {
    html.classList.remove('ih-scroll-lock');
    html.style.overflow = previous.htmlOverflow;
    body.style.overflow = previous.bodyOverflow;
  };
}
