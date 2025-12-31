async function checkAlreadyLoggedIn() {
  try {
    const res = await fetch("/auth/me");
    if (res.ok) window.location.href = "/dashboard";
  } catch {
    // ignore
  }
}

function showError(msg) {
  const el = document.getElementById("loginError");
  el.textContent = msg;
  el.style.display = "block";
  setTimeout(() => (el.style.display = "none"), 2500);
}

document.getElementById("loginForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const password = document.getElementById("password").value;

  try {
    const res = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (res.ok) {
      window.location.href = "/dashboard";
      return;
    }

    if (res.status === 400) showError("Password required");
    else showError("Invalid password");
  } catch {
    showError("Login failed");
  }
});

checkAlreadyLoggedIn();

