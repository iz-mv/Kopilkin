const AUTH_API = "http://127.0.0.1:8001";
const TRANSACTION_API = "http://127.0.0.1:8002";
const SAVINGS_API = "http://127.0.0.1:8003";

function setCurrentUser(user) {
  localStorage.setItem("kopilkin_user", JSON.stringify(user));
}

function getCurrentUser() {
  const raw = localStorage.getItem("kopilkin_user");
  return raw ? JSON.parse(raw) : null;
}

function clearCurrentUser() {
  localStorage.removeItem("kopilkin_user");
}

function redirectToLoginIfNeeded() {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
  }
  return user;
}

function formatMoney(value) {
  return `${Number(value).toLocaleString("ru-RU")} ₽`;
}

function formatDate(dateStr) {
  const date = new Date(dateStr);
  return date.toLocaleDateString("ru-RU", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }

  return data;
}

function setupAuthPage() {
  const registerForm = document.getElementById("registerForm");
  const loginForm = document.getElementById("loginForm");
  const authMessage = document.getElementById("authMessage");
  const googleLoginBtn = document.getElementById("googleLoginBtn");
  const showLoginBtn = document.getElementById("showLoginBtn");
  const showRegisterBtn = document.getElementById("showRegisterBtn");

  if (!registerForm || !loginForm) return;

  function hideForms() {
    loginForm.classList.remove("show-form");
    registerForm.classList.remove("show-form");
  }

  showLoginBtn.addEventListener("click", () => {
    hideForms();
    loginForm.classList.add("show-form");
    authMessage.textContent = "";
  });

  showRegisterBtn.addEventListener("click", () => {
    hideForms();
    registerForm.classList.add("show-form");
    authMessage.textContent = "";
  });

  registerForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const name = document.getElementById("registerName").value.trim();
    const email = document.getElementById("registerEmail").value.trim();
    const password = document.getElementById("registerPassword").value.trim();

    try {
      const user = await apiRequest(`${AUTH_API}/register`, {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });

      authMessage.textContent = `Registered successfully: ${user.name}`;
      registerForm.reset();
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });

  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const email = document.getElementById("loginEmail").value.trim();
    const password = document.getElementById("loginPassword").value.trim();

    try {
      const result = await apiRequest(`${AUTH_API}/login`, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });

      setCurrentUser({
        user_id: result.user_id,
        name: result.name,
        access_token: result.access_token,
      });

      window.location.href = "home.html";
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });

  googleLoginBtn.addEventListener("click", async () => {
    try {
      const result = await apiRequest(`${AUTH_API}/google/login`);
      authMessage.textContent = result.message || "Google login placeholder";
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });
}

function setupHomePage() {
  const user = redirectToLoginIfNeeded();
  if (!user) return;

  const avatar = document.querySelector(".avatar-circle");
  if (avatar && user.name) {
    avatar.textContent = user.name[0].toUpperCase();
  }

  setupLogoutButtons();
  setupCategoryChips();
  setTodayDate();
  loadTransactionsAndSummary(user.user_id);

  const transactionForm = document.getElementById("transactionForm");
  const refreshBtn = document.getElementById("refreshTransactionsBtn");
  const transactionMessage = document.getElementById("transactionMessage");

  transactionForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const amount = parseFloat(document.getElementById("txAmount").value);
    const date = document.getElementById("txDate").value;
    const type = document.getElementById("txType").value;
    const description = document.getElementById("txDescription").value.trim();
    const activeChip = document.querySelector(".chip.active-chip");
    const category = activeChip ? activeChip.dataset.category : "Other";

    try {
      await apiRequest(`${TRANSACTION_API}/transactions`, {
        method: "POST",
        body: JSON.stringify({
          user_id: user.user_id,
          amount,
          category,
          date,
          type,
          description: description || null,
        }),
      });

      transactionMessage.textContent = "Transaction saved successfully";
      transactionForm.reset();
      setTodayDate();
      resetActiveChip();
      loadTransactionsAndSummary(user.user_id);
    } catch (error) {
      transactionMessage.textContent = error.message;
    }
  });

  refreshBtn.addEventListener("click", () => {
    loadTransactionsAndSummary(user.user_id);
  });
}

function setupGoalsPage() {
  const user = redirectToLoginIfNeeded();
  if (!user) return;

  const avatar = document.querySelector(".avatar-circle");
  if (avatar && user.name) {
    avatar.textContent = user.name[0].toUpperCase();
  }

  setupLogoutButtons();
  loadGoals(user.user_id);

  const goalForm = document.getElementById("goalForm");
  const refreshBtn = document.getElementById("refreshGoalsBtn");
  const goalMessage = document.getElementById("goalMessage");

  goalForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const title = document.getElementById("goalTitle").value.trim();
    const target_amount = parseFloat(document.getElementById("goalTargetAmount").value);

    try {
      await apiRequest(`${SAVINGS_API}/goals`, {
        method: "POST",
        body: JSON.stringify({
          user_id: user.user_id,
          title,
          target_amount,
        }),
      });

      goalMessage.textContent = "Goal created successfully";
      goalForm.reset();
      loadGoals(user.user_id);
    } catch (error) {
      goalMessage.textContent = error.message;
    }
  });

  refreshBtn.addEventListener("click", () => {
    loadGoals(user.user_id);
  });
}

function setupLogoutButtons() {
  document.querySelectorAll("#logoutBtn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      clearCurrentUser();
      window.location.href = "login.html";
    });
  });
}

function setupCategoryChips() {
  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active-chip"));
      chip.classList.add("active-chip");
    });
  });
}

function resetActiveChip() {
  const chips = document.querySelectorAll(".chip");
  chips.forEach((chip) => chip.classList.remove("active-chip"));
  if (chips[0]) chips[0].classList.add("active-chip");
}

function setTodayDate() {
  const input = document.getElementById("txDate");
  if (input) {
    const today = new Date().toISOString().split("T")[0];
    input.value = today;
  }
}

async function loadTransactionsAndSummary(userId) {
  try {
    const [transactions, summary] = await Promise.all([
      apiRequest(`${TRANSACTION_API}/transactions/${userId}`),
      apiRequest(`${TRANSACTION_API}/transactions/${userId}/summary`),
    ]);

    renderTransactions(transactions);

    document.getElementById("todaySpent").textContent = formatMoney(
      calculateTodaySpent(transactions)
    );
    document.getElementById("totalIncome").textContent = formatMoney(summary.total_income || 0);
    document.getElementById("suggestedSave").textContent = formatMoney(
      Math.round((calculateTodaySpent(transactions) || 0) * 0.1)
    );
  } catch (error) {
    document.getElementById("transactionsList").innerHTML =
      `<p class="muted-text">${error.message}</p>`;
  }
}

function calculateTodaySpent(transactions) {
  const today = new Date().toISOString().split("T")[0];
  return transactions
    .filter((t) => t.date === today && t.type === "expense")
    .reduce((sum, t) => sum + t.amount, 0);
}

function renderTransactions(transactions) {
  const container = document.getElementById("transactionsList");
  if (!container) return;

  if (!transactions.length) {
    container.innerHTML = `<p class="muted-text">No transactions yet.</p>`;
    return;
  }

  const grouped = {};
  transactions
    .slice()
    .sort((a, b) => new Date(b.date) - new Date(a.date))
    .forEach((tx) => {
      if (!grouped[tx.date]) grouped[tx.date] = [];
      grouped[tx.date].push(tx);
    });

  container.innerHTML = Object.entries(grouped)
    .map(([date, items]) => {
      const dailyTotal = items
        .filter((i) => i.type === "expense")
        .reduce((sum, i) => sum + i.amount, 0);

      return `
        <div class="transaction-day-group">
          <div class="section-row">
            <div class="transaction-day-title">${formatDate(date)}</div>
            <div class="small-label">Spent: ${formatMoney(dailyTotal)}</div>
          </div>
          ${items
            .map(
              (tx) => `
              <div class="transaction-item">
                <div class="transaction-left">
                  <div class="transaction-category">${tx.category}</div>
                  <div class="transaction-note">${tx.description || tx.type}</div>
                </div>
                <div class="transaction-amount ${tx.type}">
                  ${tx.type === "expense" ? "-" : "+"}${formatMoney(tx.amount)}
                </div>
              </div>
            `
            )
            .join("")}
        </div>
      `;
    })
    .join("");
}

async function loadGoals(userId) {
  try {
    const goals = await apiRequest(`${SAVINGS_API}/goals/${userId}`);
    renderGoals(goals);
  } catch (error) {
    document.getElementById("goalsList").innerHTML =
      `<p class="muted-text">${error.message}</p>`;
  }
}

function renderGoals(goals) {
  const container = document.getElementById("goalsList");
  if (!container) return;

  if (!goals.length) {
    container.innerHTML = `<p class="muted-text">No goals yet.</p>`;
    return;
  }

  container.innerHTML = goals
    .map(
      (goal) => `
        <div class="goal-card">
          <div class="goal-title">${goal.title}</div>
          <div class="goal-meta">
            <span>${formatMoney(goal.current_amount)}</span>
            <span>of ${formatMoney(goal.target_amount)}</span>
          </div>
          <div class="progress-bar">
            <div class="progress-fill" style="width: ${Math.min(goal.progress_percent, 100)}%"></div>
          </div>
          <div class="goal-meta">
            <span>${goal.progress_percent}% completed</span>
          </div>
          <div class="goal-actions">
            <input type="number" step="0.01" placeholder="Add amount" id="goal-input-${goal.id}" />
            <button class="primary-btn" onclick="addMoneyToGoal('${goal.id}')">Add</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function addMoneyToGoal(goalId) {
  const input = document.getElementById(`goal-input-${goalId}`);
  const user = getCurrentUser();
  const amount = parseFloat(input.value);

  if (!amount || amount <= 0) return;

  try {
    await apiRequest(`${SAVINGS_API}/goals/${goalId}/add`, {
      method: "PATCH",
      body: JSON.stringify({ amount_to_add: amount }),
    });

    loadGoals(user.user_id);
  } catch (error) {
    alert(error.message);
  }
}