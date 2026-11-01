const tour = document.querySelector('#tour');
window.__SCENE_READY__ = true;
window.__seek = (seconds) => {
  if (tour && Number.isFinite(seconds)) tour.currentTime = Math.max(0, Math.min(seconds, tour.duration || seconds));
};
if (tour) tour.addEventListener('loadedmetadata', () => { window.__SCENE_READY__ = true; });
