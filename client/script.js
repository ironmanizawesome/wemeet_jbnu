// -----------------------------
// ✅ To-Do List 기능
// -----------------------------
const todoInput = document.querySelector(".todo-section input[type='text']");
const addBtn = document.querySelector(".todo-section button");
const todoList = document.querySelector(".todo-section ul");

addBtn.addEventListener("click", addTodo);

function addTodo() {
  const task = todoInput.value.trim();
  if (task === "") return;

  const li = document.createElement("li");
  li.innerHTML = `<input type="checkbox"> ${task} <button class="delete-btn">❌</button>`;
  todoList.appendChild(li);
  todoInput.value = "";

  // 삭제 버튼 기능
  li.querySelector(".delete-btn").addEventListener("click", () => {
    li.remove();
    saveTodos();
  });

  saveTodos();
}

// -----------------------------
// ✅ 로컬 스토리지 저장/불러오기
// -----------------------------
function saveTodos() {
  const todos = [];
  todoList.querySelectorAll("li").forEach(li => {
    const text = li.textContent.replace("❌", "").trim();
    const checked = li.querySelector("input").checked;
    todos.push({ text, checked });
  });
  localStorage.setItem("todos", JSON.stringify(todos));
}

function loadTodos() {
  const saved = localStorage.getItem("todos");
  if (!saved) return;
  JSON.parse(saved).forEach(todo => {
    const li = document.createElement("li");
    li.innerHTML = `<input type="checkbox" ${todo.checked ? "checked" : ""}> ${todo.text} <button class="delete-btn">❌</button>`;
    li.querySelector("input").addEventListener("change", saveTodos);
    li.querySelector(".delete-btn").addEventListener("click", () => {
      li.remove();
      saveTodos();
    });
    todoList.appendChild(li);
  });
}
loadTodos();

todoList.addEventListener("change", saveTodos);

// -----------------------------
// ✅ 농사 일지 저장 기능
// -----------------------------
const diaryTextarea = document.querySelector(".diary-section textarea");
const diarySaveBtn = document.createElement("button");
diarySaveBtn.textContent = "💾 저장";
diarySaveBtn.classList.add("save-btn");
document.querySelector(".diary-section").appendChild(diarySaveBtn);

diarySaveBtn.addEventListener("click", () => {
  const text = diaryTextarea.value.trim();
  if (text === "") {
    alert("내용을 입력해주세요!");
    return;
  }
  localStorage.setItem("diary", text);
  alert("🌱 일지가 저장되었습니다!");
});

window.addEventListener("load", () => {
  const savedDiary = localStorage.getItem("diary");
  if (savedDiary) diaryTextarea.value = savedDiary;
});

