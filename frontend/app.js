const AUTH_API = "http://127.0.0.1:8088/auth";
const TRANSACTION_API = "http://127.0.0.1:8088";
const SAVINGS_API = "http://127.0.0.1:8088";
const AGENT_API = "http://127.0.0.1:8088/agent";
const RECSYS_API = "http://127.0.0.1:8088";

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

function applyAvatar(element, userOrProfile, fallbackText = "U") {
  if (!element) return;

  const avatarUrl = userOrProfile?.avatar_url;

  if (avatarUrl) {
    element.textContent = "";
    element.classList.add("has-image");
    element.style.backgroundImage = `url("${avatarUrl}")`;
  } else {
    element.classList.remove("has-image");
    element.style.backgroundImage = "";
    element.textContent = fallbackText;
  }
}

async function refreshCurrentUserProfile() {
  const user = getCurrentUser();

  if (!user?.user_id) {
    return null;
  }

  try {
    const profile = await apiRequest(`${AUTH_API}/users/${user.user_id}`);

    const updatedUser = {
      ...user,
      name: profile.name,
      email: profile.email,
      avatar_url: profile.avatar_url || null,
    };

    setCurrentUser(updatedUser);

    return updatedUser;
  } catch (error) {
    console.warn("Could not refresh user profile:", error.message);
    return user;
  }
}

function refreshTopAvatar(avatarElement, user) {
  if (!avatarElement || !user) return;

  const fallbackLetter = user.name?.[0]?.toUpperCase() || "U";
  applyAvatar(avatarElement, user, fallbackLetter);

  refreshCurrentUserProfile().then((updatedUser) => {
    if (!updatedUser) return;

    const updatedFallbackLetter = updatedUser.name?.[0]?.toUpperCase() || "U";
    applyAvatar(avatarElement, updatedUser, updatedFallbackLetter);
  });
}

function redirectToLoginIfNeeded() {
  const user = getCurrentUser();
  if (!user) {
    window.location.href = "login.html";
    return null;
  }
  return user;
}

function formatMoney(value) {
  return `${Number(value || 0).toLocaleString("ru-RU")} ₽`;
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
  const isFormData = options.body instanceof FormData;

  const response = await fetch(url, {
    headers: {
      ...(isFormData ? {} : { "Content-Type": "application/json" }),
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

  showLoginBtn?.addEventListener("click", () => {
    hideForms();
    loginForm.classList.add("show-form");
    authMessage.textContent = "";
  });

  showRegisterBtn?.addEventListener("click", () => {
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
        email: result.email,
        access_token: result.access_token,
        avatar_url: result.avatar_url || null,
      });

      window.location.href = "home.html";
    } catch (error) {
      authMessage.textContent = error.message;
    }
  });

  googleLoginBtn?.addEventListener("click", async () => {
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
  refreshTopAvatar(avatar, user);

  setupLogoutButtons();
  setupTypeChips();
  renderCategoryChips("expense");
  setTodayDate();

  loadTransactionsAndSummary(user.user_id);
  loadRecommendations(user.user_id);

  const transactionForm = document.getElementById("transactionForm");
  const refreshBtn = document.getElementById("refreshTransactionsBtn");
  const refreshRecommendationsBtn = document.getElementById("refreshRecommendationsBtn");
  const transactionMessage = document.getElementById("transactionMessage");

  if (transactionForm) {
    transactionForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const rawAmount = parseFloat(document.getElementById("txAmount").value);
      const amount = Math.abs(rawAmount);
      const date = document.getElementById("txDate").value;
      const description = document.getElementById("txDescription").value.trim();

      if (!amount || amount <= 0) {
        transactionMessage.textContent = "Amount must be greater than 0";
        return;
      }

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
        loadRecommendations(user.user_id);
      } catch (error) {
        transactionMessage.textContent = error.message;
      }
    });
  }

  refreshBtn?.addEventListener("click", () => {
    loadTransactionsAndSummary(user.user_id);
  });

  refreshRecommendationsBtn?.addEventListener("click", () => {
    loadRecommendations(user.user_id);
  });
}

function setupGoalsPage() {
  const user = redirectToLoginIfNeeded();
  if (!user) return;

  const avatar = document.querySelector(".avatar-circle");
  refreshTopAvatar(avatar, user);

  setupLogoutButtons();
  setupGoalImageModal(user.user_id);
  loadGoals(user.user_id);

  const goalForm = document.getElementById("goalForm");
  const refreshBtn = document.getElementById("refreshGoalsBtn");
  const goalMessage = document.getElementById("goalMessage");

  if (goalForm) {
    goalForm.addEventListener("submit", async (e) => {
      e.preventDefault();

      const title = document.getElementById("goalTitle").value.trim();
      const rawTarget = parseFloat(document.getElementById("goalTargetAmount").value);

      if (!title) {
        goalMessage.textContent = "Goal title is required";
        return;
      }

      if (!rawTarget || rawTarget <= 0) {
        goalMessage.textContent = "Target amount must be greater than 0";
        return;
      }

      try {
        await apiRequest(`${SAVINGS_API}/goals`, {
          method: "POST",
          body: JSON.stringify({
            user_id: user.user_id,
            title,
            target_amount: rawTarget,
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

  refreshBtn?.addEventListener("click", () => {
    loadGoals(user.user_id);
  });
}

function setupProfilePage() {
  const user = redirectToLoginIfNeeded();
  if (!user) return;

  setupLogoutButtons();

  const avatar = document.getElementById("profileAvatar");
  const largeAvatar = document.getElementById("profileAvatarLarge");

  const nameText = document.getElementById("profileNameText");
  const emailText = document.getElementById("profileEmailText");
  const nameInput = document.getElementById("profileNameInput");
  const emailInput = document.getElementById("profileEmailInput");
  const userIdText = document.getElementById("profileUserId");
  const tokenText = document.getElementById("profileToken");
  const profileMessage = document.getElementById("profileMessage");
  const profileForm = document.getElementById("profileForm");

  const chooseAvatarBtn = document.getElementById("chooseAvatarBtn");
  const avatarModal = document.getElementById("avatarModal");
  const avatarModalCloseBtn = document.getElementById("avatarModalCloseBtn");
  const avatarCancelBtn = document.getElementById("avatarCancelBtn");
  const chooseAvatarInsideBtn = document.getElementById("chooseAvatarInsideBtn");
  const avatarFileInput = document.getElementById("avatarFileInput");
  const avatarCropArea = document.getElementById("avatarCropArea");
  const avatarCropImage = document.getElementById("avatarCropImage");
  const avatarEmptyState = document.getElementById("avatarEmptyState");
  const uploadAvatarBtn = document.getElementById("uploadAvatarBtn");
  const avatarModalMessage = document.getElementById("avatarModalMessage");

  let selectedAvatarFile = null;
  let selectedAvatarPreviewUrl = null;

  const cropState = {
    x: 0,
    y: 0,
    scale: 1,
    dragging: false,
    startPointerX: 0,
    startPointerY: 0,
    startImageX: 0,
    startImageY: 0,
  };

  function renderProfile(profile) {
    const fallbackLetter = profile.name?.[0]?.toUpperCase() || "U";

    applyAvatar(avatar, profile, fallbackLetter);
    applyAvatar(largeAvatar, profile, fallbackLetter);

    if (nameText) nameText.textContent = profile.name;
    if (emailText) emailText.textContent = profile.email;
    if (nameInput) nameInput.value = profile.name;
    if (emailInput) emailInput.value = profile.email;
    if (userIdText) userIdText.textContent = user.user_id;
    if (tokenText) tokenText.textContent = user.access_token || "-";
  }

  apiRequest(`${AUTH_API}/users/${user.user_id}`)
    .then((profile) => {
      renderProfile(profile);

      setCurrentUser({
        ...user,
        name: profile.name,
        email: profile.email,
        avatar_url: profile.avatar_url || null,
      });
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

        const updatedUser = {
          ...getCurrentUser(),
          name: updated.name,
          avatar_url: updated.avatar_url || null,
        };

        setCurrentUser(updatedUser);

        renderProfile(updated);

        if (profileMessage) {
          profileMessage.textContent = "Profile updated successfully";
        }
      } catch (error) {
        if (profileMessage) {
          profileMessage.textContent = error.message;
        }
      }
    });
  }

  function openAvatarModal() {
    avatarModal?.classList.remove("hidden");
    if (avatarModalMessage) avatarModalMessage.textContent = "";
  }

  function closeAvatarModal() {
    avatarModal?.classList.add("hidden");

    if (avatarModalMessage) avatarModalMessage.textContent = "";
    if (avatarFileInput) avatarFileInput.value = "";

    selectedAvatarFile = null;

    if (selectedAvatarPreviewUrl) {
      URL.revokeObjectURL(selectedAvatarPreviewUrl);
      selectedAvatarPreviewUrl = null;
    }

    if (avatarCropImage) {
      avatarCropImage.src = "";
      avatarCropImage.classList.add("hidden");
      avatarCropImage.style.width = "";
      avatarCropImage.style.height = "";
      avatarCropImage.style.transform = "";
    }

    if (avatarEmptyState) {
      avatarEmptyState.classList.remove("hidden");
    }

    cropState.x = 0;
    cropState.y = 0;
    cropState.scale = 1;
    cropState.dragging = false;
  }

  function updateCropImageTransform() {
    if (!avatarCropImage) return;

    avatarCropImage.style.transform =
      `translate(-50%, -50%) translate(${cropState.x}px, ${cropState.y}px) scale(${cropState.scale})`;
  }

  function loadImageIntoCropper(file) {
    selectedAvatarFile = file;

    if (selectedAvatarPreviewUrl) {
      URL.revokeObjectURL(selectedAvatarPreviewUrl);
    }

    selectedAvatarPreviewUrl = URL.createObjectURL(file);

    cropState.x = 0;
    cropState.y = 0;
    cropState.scale = 1;
    cropState.dragging = false;

    if (avatarModalMessage) {
      avatarModalMessage.textContent = "Drag the image to adjust crop. Scroll to zoom.";
    }

    if (avatarEmptyState) {
      avatarEmptyState.classList.add("hidden");
    }

    if (!avatarCropImage || !avatarCropArea) return;

    avatarCropImage.onload = () => {
      const areaRect = avatarCropArea.getBoundingClientRect();

      const baseScale = Math.max(
        areaRect.width / avatarCropImage.naturalWidth,
        areaRect.height / avatarCropImage.naturalHeight
      );

      avatarCropImage.style.width = `${avatarCropImage.naturalWidth * baseScale}px`;
      avatarCropImage.style.height = `${avatarCropImage.naturalHeight * baseScale}px`;

      avatarCropImage.classList.remove("hidden");
      updateCropImageTransform();
    };

    avatarCropImage.src = selectedAvatarPreviewUrl;
  }

  function createCroppedAvatarBlob() {
    return new Promise((resolve, reject) => {
      if (!selectedAvatarFile || !avatarCropArea) {
        reject(new Error("Please choose an image first"));
        return;
      }

      const image = new Image();

      image.onload = () => {
        const canvas = document.createElement("canvas");
        const size = 512;

        canvas.width = size;
        canvas.height = size;

        const ctx = canvas.getContext("2d");
        const areaRect = avatarCropArea.getBoundingClientRect();

        const baseScale = Math.max(size / image.width, size / image.height);
        const scale = baseScale * cropState.scale;

        const drawWidth = image.width * scale;
        const drawHeight = image.height * scale;

        const xRatio = size / areaRect.width;
        const yRatio = size / areaRect.height;

        const drawX = (size - drawWidth) / 2 + cropState.x * xRatio;
        const drawY = (size - drawHeight) / 2 + cropState.y * yRatio;

        ctx.clearRect(0, 0, size, size);
        ctx.drawImage(image, drawX, drawY, drawWidth, drawHeight);

        canvas.toBlob(
          (blob) => {
            if (!blob) {
              reject(new Error("Could not crop image"));
              return;
            }

            resolve(blob);
          },
          "image/jpeg",
          0.9
        );
      };

      image.onerror = () => reject(new Error("Could not load image"));
      image.src = URL.createObjectURL(selectedAvatarFile);
    });
  }

  chooseAvatarBtn?.addEventListener("click", openAvatarModal);

  avatarModalCloseBtn?.addEventListener("click", closeAvatarModal);
  avatarCancelBtn?.addEventListener("click", closeAvatarModal);

  avatarModal?.addEventListener("click", (event) => {
    if (event.target === avatarModal) {
      closeAvatarModal();
    }
  });

  chooseAvatarInsideBtn?.addEventListener("click", () => {
    avatarFileInput?.click();
  });

  avatarFileInput?.addEventListener("change", () => {
    const file = avatarFileInput.files?.[0];

    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      if (avatarModalMessage) {
        avatarModalMessage.textContent = "Only JPG, PNG and WEBP images are allowed";
      }
      return;
    }

    loadImageIntoCropper(file);
  });

  avatarCropArea?.addEventListener("pointerdown", (event) => {
    if (!selectedAvatarFile) return;

    cropState.dragging = true;
    cropState.startPointerX = event.clientX;
    cropState.startPointerY = event.clientY;
    cropState.startImageX = cropState.x;
    cropState.startImageY = cropState.y;

    avatarCropArea.setPointerCapture(event.pointerId);
  });

  avatarCropArea?.addEventListener("pointermove", (event) => {
    if (!cropState.dragging) return;

    const deltaX = event.clientX - cropState.startPointerX;
    const deltaY = event.clientY - cropState.startPointerY;

    cropState.x = cropState.startImageX + deltaX;
    cropState.y = cropState.startImageY + deltaY;

    updateCropImageTransform();
  });

  avatarCropArea?.addEventListener("pointerup", (event) => {
    cropState.dragging = false;

    try {
      avatarCropArea.releasePointerCapture(event.pointerId);
    } catch (_) {}
  });

  avatarCropArea?.addEventListener("pointercancel", () => {
    cropState.dragging = false;
  });

  avatarCropArea?.addEventListener("pointerleave", () => {
    cropState.dragging = false;
  });

  avatarCropArea?.addEventListener("wheel", (event) => {
    if (!selectedAvatarFile) return;

    event.preventDefault();

    const direction = event.deltaY < 0 ? 1 : -1;
    const nextScale = cropState.scale + direction * 0.08;

    cropState.scale = Math.min(Math.max(nextScale, 1), 3);

    updateCropImageTransform();
  });

  uploadAvatarBtn?.addEventListener("click", async () => {
    try {
      if (!selectedAvatarFile) {
        avatarModalMessage.textContent = "Please choose an image first";
        return;
      }

      avatarModalMessage.textContent = "Uploading avatar...";

      const croppedBlob = await createCroppedAvatarBlob();

      const formData = new FormData();
      formData.append("file", croppedBlob, "avatar.jpg");

      const currentUser = getCurrentUser();

      const updated = await apiRequest(`${AUTH_API}/me/avatar`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${currentUser.access_token}`,
        },
        body: formData,
      });

      const updatedUser = {
        ...currentUser,
        name: updated.name,
        email: updated.email,
        avatar_url: updated.avatar_url || null,
      };

      setCurrentUser(updatedUser);

      renderProfile(updated);

      avatarModalMessage.textContent = "Avatar updated successfully";

      setTimeout(() => {
        closeAvatarModal();
      }, 500);
    } catch (error) {
      avatarModalMessage.textContent = error.message;
    }
  });
}

function setupAIPage() {
  const user = redirectToLoginIfNeeded();
  if (!user) return;

  setupLogoutButtons();

  const avatar = document.querySelector(".avatar-circle");
  refreshTopAvatar(avatar, user);

  const form = document.getElementById("aiChatForm");
  const input = document.getElementById("aiChatInput");
  const messages = document.getElementById("aiChatMessages");
  const status = document.getElementById("aiChatStatus");
  const sendBtn = document.getElementById("aiSendBtn");

  if (!form || !input || !messages || !sendBtn) return;

  function addMessage(text, type) {
    const message = document.createElement("div");
    message.className = `ai-page-message ai-page-message-${type}`;
    message.textContent = text;

    messages.appendChild(message);
    messages.scrollTop = messages.scrollHeight;
  }

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const question = input.value.trim();
    if (!question) return;

    addMessage(question, "user");
    input.value = "";

    const loadingMessage = document.createElement("div");
    loadingMessage.className = "ai-page-message ai-page-message-bot";
    loadingMessage.textContent = "Thinking...";
    messages.appendChild(loadingMessage);
    messages.scrollTop = messages.scrollHeight;

    sendBtn.disabled = true;
    sendBtn.textContent = "Waiting...";
    if (status) status.textContent = "Kopilkin AI is analyzing your data...";

    try {
      const result = await apiRequest(`${AGENT_API}/chat`, {
        method: "POST",
        body: JSON.stringify({
          user_id: user.user_id,
          message: question,
        }),
      });

      loadingMessage.textContent = result.response || "No response from assistant.";
      if (status) status.textContent = "";
    } catch (error) {
      loadingMessage.textContent = `AI error: ${error.message}`;
      if (status) status.textContent = "Could not reach AI assistant.";
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = "Send message";
      messages.scrollTop = messages.scrollHeight;
    }
  });
}

function setupLogoutButtons() {
  document.querySelectorAll("#logoutBtn").forEach((btn) => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();

      const user = getCurrentUser();

      try {
        if (user?.access_token) {
          await apiRequest(`${AUTH_API}/logout`, {
            method: "POST",
            body: JSON.stringify({
              access_token: user.access_token,
            }),
          });
        }
      } catch (error) {
        console.warn("Backend logout failed:", error.message);
      } finally {
        clearCurrentUser();
        window.location.href = "login.html";
      }
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
    const container = document.getElementById("transactionsList");
    if (container) {
      container.innerHTML = `<p class="muted-text">${error.message}</p>`;
    }
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
        .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));

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
    loadRecommendations(user.user_id);
  } catch (error) {
    alert(error.message);
  }
}

async function loadRecommendations(userId) {
  const container = document.getElementById("recommendationsList");
  if (!container) return;

  container.innerHTML = `<p class="muted-text">Loading recommendations...</p>`;

  try {
    const result = await apiRequest(`${RECSYS_API}/recommendations/${userId}`);
    renderRecommendations(result.recommendations || []);
  } catch (error) {
    container.innerHTML = `<p class="muted-text">Could not load recommendations: ${error.message}</p>`;
  }
}

function renderRecommendations(recommendations) {
  const container = document.getElementById("recommendationsList");
  if (!container) return;

  if (!recommendations.length) {
    container.innerHTML = `<p class="muted-text">No recommendations yet.</p>`;
    return;
  }

  container.innerHTML = recommendations
    .map((recommendation) => `
      <div class="recommendation-card">
        <div class="recommendation-top">
          <div>
            <div class="recommendation-title">${recommendation.title}</div>
            <div class="small-label">${formatRecommendationType(recommendation.type)}</div>
          </div>
          <span class="recommendation-badge">${formatApproachName(recommendation.approach)}</span>
        </div>
        <p class="recommendation-description">${recommendation.description}</p>
      </div>
    `)
    .join("");
}

function formatApproachName(approach) {
  if (!approach) return "RecSys";

  const names = {
    heuristic: "Heuristic",
    content_based: "Content-based",
    collaborative_filtering: "Collaborative"
  };

  return names[approach] || approach;
}

function formatRecommendationType(type) {
  if (!type) return "Personal recommendation";

  const names = {
    cold_start: "Cold start",
    saving_rule: "Saving rule",
    overspending_alert: "Overspending alert",
    category_based: "Category-based advice",
    similar_users: "Similar users"
  };

  return names[type] || type.replaceAll("_", " ");
}


let goalImageModalInitialized = false;
let goalImageCurrentGoalId = null;
let goalImageSelectedFile = null;
let goalImageSelectedPreviewUrl = null;
let goalImageCurrentUserId = null;
let goalImageElements = null;

const goalImageCropState = {
  x: 0,
  y: 0,
  scale: 1,
  dragging: false,
  startPointerX: 0,
  startPointerY: 0,
  startImageX: 0,
  startImageY: 0,
};

function setupGoalImageModal(userId) {
  goalImageCurrentUserId = userId;

  if (goalImageModalInitialized) return;

  goalImageElements = {
    modal: document.getElementById("goalImageModal"),
    closeBtn: document.getElementById("goalImageModalCloseBtn"),
    cancelBtn: document.getElementById("goalImageCancelBtn"),
    chooseBtn: document.getElementById("chooseGoalImageInsideBtn"),
    fileInput: document.getElementById("goalImageFileInput"),
    cropArea: document.getElementById("goalImageCropArea"),
    cropImage: document.getElementById("goalImageCropImage"),
    emptyState: document.getElementById("goalImageEmptyState"),
    uploadBtn: document.getElementById("uploadGoalImageBtn"),
    message: document.getElementById("goalImageModalMessage"),
  };

  if (!goalImageElements.modal) return;

  goalImageElements.closeBtn?.addEventListener("click", closeGoalImageModal);
  goalImageElements.cancelBtn?.addEventListener("click", closeGoalImageModal);

  goalImageElements.modal?.addEventListener("click", (event) => {
    if (event.target === goalImageElements.modal) {
      closeGoalImageModal();
    }
  });

  goalImageElements.chooseBtn?.addEventListener("click", () => {
    goalImageElements.fileInput?.click();
  });

  goalImageElements.fileInput?.addEventListener("change", () => {
    const file = goalImageElements.fileInput.files?.[0];

    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      if (goalImageElements.message) {
        goalImageElements.message.textContent = "Only JPG, PNG and WEBP images are allowed";
      }
      return;
    }

    loadGoalImageIntoCropper(file);
  });

  goalImageElements.cropArea?.addEventListener("pointerdown", (event) => {
    if (!goalImageSelectedFile) return;

    goalImageCropState.dragging = true;
    goalImageCropState.startPointerX = event.clientX;
    goalImageCropState.startPointerY = event.clientY;
    goalImageCropState.startImageX = goalImageCropState.x;
    goalImageCropState.startImageY = goalImageCropState.y;

    goalImageElements.cropArea.setPointerCapture(event.pointerId);
  });

  goalImageElements.cropArea?.addEventListener("pointermove", (event) => {
    if (!goalImageCropState.dragging) return;

    const deltaX = event.clientX - goalImageCropState.startPointerX;
    const deltaY = event.clientY - goalImageCropState.startPointerY;

    goalImageCropState.x = goalImageCropState.startImageX + deltaX;
    goalImageCropState.y = goalImageCropState.startImageY + deltaY;

    updateGoalImageTransform();
  });

  goalImageElements.cropArea?.addEventListener("pointerup", (event) => {
    goalImageCropState.dragging = false;

    try {
      goalImageElements.cropArea.releasePointerCapture(event.pointerId);
    } catch (_) {}
  });

  goalImageElements.cropArea?.addEventListener("pointerleave", () => {
    goalImageCropState.dragging = false;
  });

  goalImageElements.cropArea?.addEventListener("wheel", (event) => {
    if (!goalImageSelectedFile) return;

    event.preventDefault();

    const direction = event.deltaY < 0 ? 1 : -1;
    const nextScale = goalImageCropState.scale + direction * 0.08;

    goalImageCropState.scale = Math.min(Math.max(nextScale, 1), 3);

    updateGoalImageTransform();
  });

  goalImageElements.uploadBtn?.addEventListener("click", uploadCroppedGoalImage);

  goalImageModalInitialized = true;
}

function openGoalImageModal(goalId) {
  goalImageCurrentGoalId = goalId;

  if (!goalImageElements?.modal) {
    return;
  }

  resetGoalImageCropper();
  goalImageElements.modal.classList.remove("hidden");

  if (goalImageElements.message) {
    goalImageElements.message.textContent = "Choose an image to continue";
  }
}

function closeGoalImageModal() {
  goalImageElements?.modal?.classList.add("hidden");
  resetGoalImageCropper();
  goalImageCurrentGoalId = null;
}

function resetGoalImageCropper() {
  if (goalImageElements?.message) goalImageElements.message.textContent = "";
  if (goalImageElements?.fileInput) goalImageElements.fileInput.value = "";

  goalImageSelectedFile = null;

  if (goalImageSelectedPreviewUrl) {
    URL.revokeObjectURL(goalImageSelectedPreviewUrl);
    goalImageSelectedPreviewUrl = null;
  }

  if (goalImageElements?.cropImage) {
    goalImageElements.cropImage.src = "";
    goalImageElements.cropImage.classList.add("hidden");
    goalImageElements.cropImage.style.width = "";
    goalImageElements.cropImage.style.height = "";
    goalImageElements.cropImage.style.transform = "";
  }

  goalImageElements?.emptyState?.classList.remove("hidden");

  goalImageCropState.x = 0;
  goalImageCropState.y = 0;
  goalImageCropState.scale = 1;
  goalImageCropState.dragging = false;
}

function updateGoalImageTransform() {
  if (!goalImageElements?.cropImage) return;

  goalImageElements.cropImage.style.transform =
    `translate(-50%, -50%) translate(${goalImageCropState.x}px, ${goalImageCropState.y}px) scale(${goalImageCropState.scale})`;
}

function loadGoalImageIntoCropper(file) {
  goalImageSelectedFile = file;

  if (goalImageSelectedPreviewUrl) {
    URL.revokeObjectURL(goalImageSelectedPreviewUrl);
  }

  goalImageSelectedPreviewUrl = URL.createObjectURL(file);

  goalImageCropState.x = 0;
  goalImageCropState.y = 0;
  goalImageCropState.scale = 1;

  if (goalImageElements.message) {
    goalImageElements.message.textContent = "Drag the image to adjust crop. Scroll to zoom.";
  }

  goalImageElements.emptyState?.classList.add("hidden");

  const cropImage = goalImageElements.cropImage;
  const cropArea = goalImageElements.cropArea;

  if (!cropImage || !cropArea) return;

  cropImage.onload = () => {
    const areaRect = cropArea.getBoundingClientRect();

    const baseScale = Math.max(
      areaRect.width / cropImage.naturalWidth,
      areaRect.height / cropImage.naturalHeight,
    );

    cropImage.style.width = `${cropImage.naturalWidth * baseScale}px`;
    cropImage.style.height = `${cropImage.naturalHeight * baseScale}px`;

    cropImage.classList.remove("hidden");
    updateGoalImageTransform();
  };

  cropImage.src = goalImageSelectedPreviewUrl;
}

function createCroppedGoalImageBlob() {
  return new Promise((resolve, reject) => {
    if (!goalImageSelectedFile || !goalImageElements?.cropArea) {
      reject(new Error("Please choose an image first"));
      return;
    }

    const image = new Image();

    image.onload = () => {
      const canvas = document.createElement("canvas");
      const width = 960;
      const height = 540;

      canvas.width = width;
      canvas.height = height;

      const ctx = canvas.getContext("2d");
      const areaRect = goalImageElements.cropArea.getBoundingClientRect();

      const baseScale = Math.max(width / image.width, height / image.height);
      const scale = baseScale * goalImageCropState.scale;

      const drawWidth = image.width * scale;
      const drawHeight = image.height * scale;

      const xRatio = width / areaRect.width;
      const yRatio = height / areaRect.height;

      const drawX = (width - drawWidth) / 2 + goalImageCropState.x * xRatio;
      const drawY = (height - drawHeight) / 2 + goalImageCropState.y * yRatio;

      ctx.clearRect(0, 0, width, height);
      ctx.drawImage(image, drawX, drawY, drawWidth, drawHeight);

      canvas.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Could not crop image"));
            return;
          }

          resolve(blob);
        },
        "image/jpeg",
        0.9,
      );
    };

    image.onerror = () => reject(new Error("Could not load image"));
    image.src = URL.createObjectURL(goalImageSelectedFile);
  });
}

async function uploadCroppedGoalImage() {
  try {
    if (!goalImageCurrentGoalId) {
      goalImageElements.message.textContent = "Goal is not selected";
      return;
    }

    if (!goalImageSelectedFile) {
      goalImageElements.message.textContent = "Please choose an image first";
      return;
    }

    goalImageElements.message.textContent = "Uploading goal image...";

    const croppedBlob = await createCroppedGoalImageBlob();

    const formData = new FormData();
    formData.append("file", croppedBlob, "goal-cover.jpg");

    await apiRequest(`${SAVINGS_API}/goals/${goalImageCurrentGoalId}/image`, {
      method: "POST",
      body: formData,
    });

    goalImageElements.message.textContent = "Goal image updated successfully";

    if (goalImageCurrentUserId) {
      loadGoals(goalImageCurrentUserId);
    }

    setTimeout(() => {
      closeGoalImageModal();
    }, 500);
  } catch (error) {
    goalImageElements.message.textContent = error.message;
  }
}

async function loadGoals(userId) {
  try {
    const goals = await apiRequest(`${SAVINGS_API}/goals/${userId}`);
    renderGoals(goals);
  } catch (error) {
    const container = document.getElementById("goalsList");
    if (container) {
      container.innerHTML = `<p class="muted-text">${error.message}</p>`;
    }
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
    .map((goal) => {
      const currentAmount = Number(goal.current_amount || 0);
      const targetAmount = Number(goal.target_amount || 0);

      const progressPercent = targetAmount > 0
        ? Math.round((currentAmount / targetAmount) * 100)
        : 0;

      const safeProgressPercent = Math.min(Math.max(progressPercent, 0), 100);
      const safeImageUrl = goal.image_url ? String(goal.image_url).replaceAll('"', '&quot;') : "";

      return `
        <div class="goal-card">
          <div
            class="goal-image-cover ${goal.image_url ? "has-goal-image" : ""}"
            ${goal.image_url ? `style="background-image: url(&quot;${safeImageUrl}&quot;)"` : ""}
          >
            ${goal.image_url ? "" : `<span class="goal-image-placeholder-icon">🎯</span>`}
          </div>

          <div class="goal-card-header-row">
            <div>
              <div class="goal-title">${goal.title}</div>
              <div class="small-label">Savings target</div>
            </div>

            <button
              type="button"
              class="secondary-btn goal-image-btn"
              onclick="openGoalImageModal('${goal.id}')"
            >
              ${goal.image_url ? "Change image" : "Add image"}
            </button>
          </div>

          <div class="goal-meta">
            <span>${formatMoney(currentAmount)}</span>
            <span>of ${formatMoney(targetAmount)}</span>
          </div>

          <div class="progress-bar">
            <div class="progress-fill" style="width: ${safeProgressPercent}%"></div>
          </div>

          <div class="goal-meta">
            <span>${progressPercent}% completed</span>
          </div>

          <div class="goal-actions">
            <input type="number" step="0.01" placeholder="Use + amount" id="goal-input-${goal.id}" />
            <button class="primary-btn" onclick="addMoneyToGoal('${goal.id}')">Apply</button>
          </div>
        </div>
      `;
    })
    .join("");
}

async function addMoneyToGoal(goalId) {
  const input = document.getElementById(`goal-input-${goalId}`);
  const user = getCurrentUser();
  const amount = parseFloat(input.value);

  if (!amount || amount <= 0) {
    alert("Amount must be greater than 0");
    return;
  }

  try {
    await apiRequest(`${SAVINGS_API}/goals/${goalId}/add`, {
      method: "PATCH",
      body: JSON.stringify({ amount: amount }),
    });

    input.value = "";
    loadGoals(user.user_id);
  } catch (error) {
    alert(error.message);
  }
}
