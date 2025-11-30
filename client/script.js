const API_BASE = window.API_BASE_URL || "http://127.0.0.1:8000";
const username =
  sessionStorage.getItem("username") ||
  sessionStorage.getItem("userName") ||
  "";

if (!username) {
  alert("로그인이 필요합니다.");
  window.location.href = "login.html";
}

// -----------------------------
// ✅ To-Do List 기능
// -----------------------------
const todoInput = document.querySelector(".todo-section input[type='text']");
const addBtn = document.querySelector(".todo-section button");
const todoList = document.querySelector(".todo-section ul");

function createTodoElement(todo) {
  const li = document.createElement("li");
  li.className = "todo-item";
  li.dataset.text = todo.text;

  const checkbox = document.createElement("input");
  checkbox.type = "checkbox";
  checkbox.checked = !!todo.checked;

  const span = document.createElement("span");
  span.textContent = todo.text;

  const deleteBtn = document.createElement("button");
  deleteBtn.className = "delete-btn";
  deleteBtn.textContent = "❌";

  checkbox.addEventListener("change", saveTodos);
  deleteBtn.addEventListener("click", () => {
    li.remove();
    saveTodos();
  });

  li.appendChild(checkbox);
  li.appendChild(span);
  li.appendChild(deleteBtn);
  todoList.appendChild(li);
}

function addTodo() {
  const task = todoInput.value.trim();
  if (!task) return;
  createTodoElement({ text: task, checked: false });
  todoInput.value = "";
  saveTodos();
}

addBtn.addEventListener("click", addTodo);
todoInput.addEventListener("keypress", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    addTodo();
  }
});

function getTodosSnapshot() {
  const todos = [];
  todoList.querySelectorAll("li").forEach((li) => {
    const checkbox = li.querySelector("input[type='checkbox']");
    const text = li.dataset.text || li.querySelector("span")?.textContent || "";
    todos.push({
      text: text.trim(),
      checked: checkbox?.checked ?? false,
    });
  });
  return todos;
}

function saveTodos() {
  const todos = getTodosSnapshot();
  localStorage.setItem("todos", JSON.stringify(todos));
}

function hydrateTodos(todos = []) {
  todoList.innerHTML = "";
  todos.forEach((todo) => {
    if (!todo || !todo.text) return;
    createTodoElement({
      text: todo.text,
      checked: !!todo.checked,
    });
  });
}

function loadTodosFromLocal() {
  try {
    const saved = JSON.parse(localStorage.getItem("todos") || "[]");
    hydrateTodos(saved);
  } catch (err) {
    console.warn("저장된 할 일을 불러오지 못했습니다:", err);
  }
}

loadTodosFromLocal();

// -----------------------------
// ✅ 농사 일지 저장 기능 (MongoDB 연동)
// -----------------------------
const diarySection = document.querySelector(".diary-section");
const diaryTextarea = diarySection.querySelector("textarea");
const diarySaveBtn = document.createElement("button");
diarySaveBtn.textContent = "💾 저장";
diarySaveBtn.classList.add("save-btn");
diarySection.appendChild(diarySaveBtn);

const diaryStatus = document.createElement("p");
diaryStatus.className = "diary-status";
diarySection.appendChild(diaryStatus);

function setDiaryStatus(message, isError = false) {
  diaryStatus.textContent = message;
  diaryStatus.style.color = isError ? "#f87171" : "#94a3b8";
}

async function loadDiaryFromServer() {
  setDiaryStatus("최근 일지를 불러오는 중입니다...");
  try {
    const res = await fetch(
      `${API_BASE}/diaries/${encodeURIComponent(username)}`
    );
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    if (Array.isArray(data.diaries) && data.diaries.length) {
      const latest = data.diaries[0];
      diaryTextarea.value = latest.content || "";
      localStorage.setItem("diary", latest.content || "");
      const todos = Array.isArray(latest.todos) ? latest.todos : [];
      hydrateTodos(todos);
      localStorage.setItem("todos", JSON.stringify(todos));
      setDiaryStatus(
        `마지막 저장: ${new Date(latest.updated_at).toLocaleString()}`
      );
    } else {
      const savedDiary = localStorage.getItem("diary");
      diaryTextarea.value = savedDiary || "";
      setDiaryStatus("저장된 일지가 없습니다. 새로 작성해 보세요!");
    }
  } catch (error) {
    console.error(error);
    setDiaryStatus("서버에서 일지를 불러오지 못했습니다. 다시 시도해 주세요.", true);
    const savedDiary = localStorage.getItem("diary");
    if (savedDiary) diaryTextarea.value = savedDiary;
  }
}

async function saveDiary() {
  const content = diaryTextarea.value.trim();
  if (!content) {
    alert("내용을 입력해주세요!");
    return;
  }

  const payload = {
    userId: username,
    content,
    date: new Date().toISOString().slice(0, 10),
    todos: getTodosSnapshot(),
  };

  diarySaveBtn.disabled = true;
  setDiaryStatus("저장 중입니다...");

  try {
    const res = await fetch(`${API_BASE}/diaries`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      throw new Error(await res.text());
    }

    const data = await res.json();
    localStorage.setItem("diary", content);
    localStorage.setItem("todos", JSON.stringify(payload.todos));
    setDiaryStatus(
      `저장 완료: ${new Date(data.updated_at).toLocaleString()}`
    );
  } catch (error) {
    console.error(error);
    setDiaryStatus("저장에 실패했습니다. 다시 시도해 주세요.", true);
  } finally {
    diarySaveBtn.disabled = false;
  }
}

diarySaveBtn.addEventListener("click", saveDiary);

window.addEventListener("load", () => {
  const savedDiary = localStorage.getItem("diary");
  if (savedDiary) diaryTextarea.value = savedDiary;
  loadDiaryFromServer();
});
