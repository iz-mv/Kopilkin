const AUTH_API = "http://127.0.0.1:8001";
const TRANSACTION_API = "http://127.0.0.1:8002";
const SAVINGS_API = "http://127.0.0.1:8003";

const EXPENSE_CATEGORIES = [
  "Restaurants",
  "Transport",
  "Groceries",
  "Shopping",
  "Health",
  "Entertainment",
  "Bills",
  "Travel",
  "Education",
  "Other"
];

const INCOME_CATEGORIES = [
  "Salary",
  "Bonus",
  "Cashback",
  "Gift",
  "Support",
  "Freelance",
  "Refund",
  "Other"
];

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
  setupTypeChips();
  renderCategoryChips("expense");
  setTodayDate();
  loadTransactionsAndSummary(user.user_id);

  const transactionForm = document.getElementById("transactionForm");
  const refreshBtn = document.getElementById("refreshTransactionsBtn");
  const transactionMessage = document.getElementById("transactionMessage");

  if (transactionForm) {
    transactionForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const rawAmount = parseFloat(document.getElementById("txAmount").value);
      const amount = Math.abs(rawAmount);
      const date = document.getElementById("txDate").value;
      const description = document.getElementById("txDescription").value.trim();

      const activeTypeChip = document.querySelector(".type-chip.active-type-chip");
      const type = activeTypeChip ? activeTypeChip.dataset.type : "expense";

      const activeCategoryChip = document.querySelector("#categoryChips .chip.active-chip");
      const category = activeCategoryChip ? activeCategoryChip.dataset.category : "Other";

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
        renderCategoryChips(type);
        loadTransactionsAndSummary(user.user_id);
      } catch (error) {
        transactionMessage.textContent = error.message;
      }
    });
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loadTransactionsAndSummary(user.user_id);
    });
  }
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

  if (goalForm) {
    goalForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const title = document.getElementById("goalTitle").value.trim();
      const target_amount = Math.abs(parseFloat(document.getElementById("goalTargetAmount").value));

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
  }

  if (refreshBtn) {
    refreshBtn.addEventListener("click", () => {
      loadGoals(user.user_id);
    });
  }
}

function setupProfilePage() {
  const user = redirectToLoginIfNeeded();
  if (!user) return;

  setupLogoutButtons();

  const avatar = document.getElementById("profileAvatar");
  const nameText = document.getElementById("profileNameText");
  const emailText = document.getElementById("profileEmailText");
  const nameInput = document.getElementById("profileNameInput");
  const emailInput = document.getElementById("profileEmailInput");
  const userIdText = document.getElementById("profileUserId");
  const tokenText = document.getElementById("profileToken");
  const profileMessage = document.getElementById("profileMessage");
  const profileForm = document.getElementById("profileForm");

  apiRequest(`${AUTH_API}/users/${user.user_id}`)
    .then((profile) => {
      if (avatar) avatar.textContent = profile.name[0].toUpperCase();
      if (nameText) nameText.textContent = profile.name;
      if (emailText) emailText.textContent = profile.email;
      if (nameInput) nameInput.value = profile.name;
      if (emailInput) emailInput.value = profile.email;
      if (userIdText) userIdText.textContent = user.user_id;
      if (tokenText) tokenText.textContent = user.access_token || "-";
    })
    .catch((error) => {
      if (profileMessage) profileMessage.textContent = error.message;
    });

  if (profileForm) {
    profileForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const newName = nameInput.value.trim();

      try {
        const updated = await apiRequest(`${AUTH_API}/users/${user.user_id}`, {
          method: "PATCH",
          body: JSON.stringify({ name: newName }),
        });

        setCurrentUser({
          ...user,
          name: updated.name,
        });

        if (avatar) avatar.textContent = updated.name[0].toUpperCase();
        if (nameText) nameText.textContent = updated.name;

        profileMessage.textContent = "Profile updated successfully";
      } catch (error) {
        profileMessage.textContent = error.message;
      }
    });
  }
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

function setupTypeChips() {
  document.querySelectorAll(".type-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".type-chip").forEach((c) => c.classList.remove("active-type-chip"));
      chip.classList.add("active-type-chip");
      renderCategoryChips(chip.dataset.type);
    });
  });
}

function renderCategoryChips(type) {
  const container = document.getElementById("categoryChips");
  if (!container) return;

  const categories = type === "income" ? INCOME_CATEGORIES : EXPENSE_CATEGORIES;

  container.innerHTML = categories
    .map((category, index) => `
      <button
        type="button"
        class="chip ${index === 0 ? "active-chip" : ""}"
        data-category="${category}"
      >
        ${category}
      </button>
    `)
    .join("");

  container.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      container.querySelectorAll(".chip").forEach((c) => c.classList.remove("active-chip"));
      chip.classList.add("active-chip");
    });
  });
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

    const todaySpent = calculateTodaySpent(transactions);
    const todayIncome = calculateTodayIncome(transactions);

    document.getElementById("todaySpent").textContent = formatMoney(todaySpent);
    document.getElementById("totalIncome").textContent = formatMoney(summary.total_income || 0);

    const suggested = todayIncome > 0
      ? Math.round(todayIncome * 0.1)
      : Math.round(todaySpent * 0.1);

    document.getElementById("suggestedSave").textContent = formatMoney(suggested);
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

function calculateTodayIncome(transactions) {
  const today = new Date().toISOString().split("T")[0];
  return transactions
    .filter((t) => t.date === today && t.type === "income")
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
  transactions.forEach((tx) => {
    if (!grouped[tx.date]) grouped[tx.date] = [];
    grouped[tx.date].push(tx);
  });

  container.innerHTML = Object.entries(grouped)
    .sort((a, b) => new Date(b[0]) - new Date(a[0]))
    .map(([date, items]) => {
      const sortedItems = items
        .slice()
        .sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

      const dailyTotal = sortedItems
        .filter((i) => i.type === "expense")
        .reduce((sum, i) => sum + i.amount, 0);

      return `
        <div class="transaction-day-group">
          <div class="section-row">
            <div class="transaction-day-title">${formatDate(date)}</div>
            <div class="small-label">Spent: ${formatMoney(dailyTotal)}</div>
          </div>
          ${sortedItems
            .map(
              (tx) => `
              <div class="transaction-item">
                <div class="transaction-left">
                  <div class="transaction-category">${tx.category}</div>
                  <div class="transaction-note">${tx.description || tx.type}</div>
                </div>
                <div class="transaction-right">
                  <div class="transaction-amount ${tx.type}">
                    ${tx.type === "expense" ? "-" : "+"}${formatMoney(tx.amount)}
                  </div>
                  <button class="delete-btn" onclick="deleteTransaction('${tx.id}')">Delete</button>
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

async function deleteTransaction(transactionId) {
  const user = getCurrentUser();
  if (!user) return;

  try {
    await apiRequest(`${TRANSACTION_API}/transactions/${transactionId}`, {
      method: "DELETE",
    });

    loadTransactionsAndSummary(user.user_id);
  } catch (error) {
    alert(error.message);
  }
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
            <input type="number" step="0.01" min="0.01" placeholder="Add amount" id="goal-input-${goal.id}" />
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

  if (!amount || amount === 0) return;

  try {
    await apiRequest(`${SAVINGS_API}/goals/${goalId}/add`, {
      method: "PATCH",
      body: JSON.stringify({ amount_change: amount }),
    });

    loadGoals(user.user_id);
  } catch (error) {
    alert(error.message);
  }
}