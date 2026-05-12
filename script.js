document.querySelectorAll("video").forEach(video => {
  video.addEventListener("ended", function () {
    this.currentTime = 0;
    this.play();
  });
});