const taskForm = document.getElementById("taskForm");
const taskTitle = document.getElementById("taskTitle");
const taskPriority = document.getElementById("taskPriority");
const taskList = document.getElementById("taskList");
const emptyState = document.getElementById("emptyState");
const searchInput = document.getElementById("searchInput");
const addTaskBtn = document.getElementById("addTaskBtn");
const totalCount = document.getElementById("totalCount");
const doneCount = document.getElementById("doneCount");
const pendingCount = document.getElementById("pendingCount");
const taskTemplate = document.getElementById("taskTemplate");

let tasks = [
  { id: 1, title: "Review pull request", priority: "high", done: false },
  { id: 2, title: "Test AI review bot", priority: "medium", done: false },
];

function updateStats() {
  const done = tasks.filter((task) => task.done).length;
  totalCount.textContent = String(tasks.length);
  doneCount.textContent = String(done);
  pendingCount.textContent = String(tasks.length - done);
}

function renderTasks() {
  const query = searchInput.value.trim().toLowerCase();
  const filtered = tasks.filter((task) => task.title.toLowerCase().includes(query));

  taskList.innerHTML = "";
  emptyState.classList.toggle("hidden", filtered.length > 0);

  filtered.forEach((task) => {
    const node = taskTemplate.content.cloneNode(true);
    const item = node.querySelector(".task-item");
    const checkbox = node.querySelector(".task-done");
    const title = node.querySelector(".task-title");
    const priority = node.querySelector(".task-priority");
    const deleteBtn = node.querySelector(".task-delete");

    checkbox.checked = task.done;
    title.textContent = task.title;
    priority.textContent = task.priority;
    priority.classList.add(task.priority);
    item.classList.toggle("done", task.done);

    checkbox.addEventListener("change", () => {
      task.done = checkbox.checked;
      renderTasks();
      updateStats();
    });

    deleteBtn.addEventListener("click", () => {
      tasks = tasks.filter((entry) => entry.id !== task.id);
      renderTasks();
      updateStats();
    });

    taskList.appendChild(node);
  });
}

taskForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const title = taskTitle.value.trim();
  if (!title) {
    return;
  }

  tasks.unshift({
    id: Date.now(),
    title,
    priority: taskPriority.value,
    done: false,
  });

  taskForm.reset();
  taskPriority.value = "medium";
  renderTasks();
  updateStats();
});

searchInput.addEventListener("input", renderTasks);

addTaskBtn.addEventListener("click", () => {
  taskTitle.focus();
});

renderTasks();
updateStats();
