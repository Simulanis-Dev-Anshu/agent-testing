const tabs = document.querySelectorAll(".tab");
const openModalBtn = document.getElementById("openModalBtn");
const closeModalBtn = document.getElementById("closeModalBtn");
const reviewModal = document.getElementById("reviewModal");
const feedbackForm = document.getElementById("feedbackForm");
const formMessage = document.getElementById("formMessage");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    tabs.forEach((item) => item.classList.remove("active"));
    tab.classList.add("active");
  });
});

function openModal() {
  reviewModal.classList.remove("hidden");
}

function closeModal() {
  reviewModal.classList.add("hidden");
}

openModalBtn.addEventListener("click", openModal);
closeModalBtn.addEventListener("click", closeModal);

document.querySelectorAll("[data-close-modal]").forEach((element) => {
  element.addEventListener("click", closeModal);
});

feedbackForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const formData = new FormData(feedbackForm);
  const title = formData.get("title");

  formMessage.textContent = `Thanks! Feedback "${title}" was submitted.`;
  formMessage.classList.remove("hidden");
  feedbackForm.reset();
});
