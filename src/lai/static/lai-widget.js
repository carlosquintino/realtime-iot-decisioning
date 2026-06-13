/* LAI — widget de chat flutuante.
 * Injetado em todas as páginas da UI Magistrala via nginx sub_filter.
 * Sem dependências; usa os endpoints /lai/* (mesma origem).
 */
(function () {
  if (window.__laiLoaded) return;
  window.__laiLoaded = true;

  var API = {
    me: "/lai/me",
    login: "/lai/login",
    chat: "/lai/chat",
    logout: "/lai/logout",
  };
  var history = [];
  var SUGGESTIONS = [
    "Qual foi a última irrigação?",
    "Mostre os últimos dados da fazenda",
    "Qual cultura estou cultivando?",
    "Quanto de nitrogênio foi aplicado no total?",
    "Resuma as decisões da temporada",
    "Qual o estado atual da lavoura?",
  ];

  // ── estilos ────────────────────────────────────────────────────────────────
  var css = `
  #lai-fab{position:fixed;right:24px;bottom:24px;width:60px;height:60px;border-radius:50%;
    background:#1565c0;color:#fff;border:none;box-shadow:0 4px 14px rgba(0,0,0,.3);
    font-weight:700;font-size:18px;cursor:pointer;z-index:99999}
  #lai-panel{position:fixed;right:24px;bottom:96px;width:360px;max-width:92vw;height:520px;
    max-height:78vh;background:#fff;border-radius:14px;box-shadow:0 8px 30px rgba(0,0,0,.35);
    display:none;flex-direction:column;overflow:hidden;z-index:99999;font-family:system-ui,Arial,sans-serif}
  #lai-panel.open{display:flex}
  #lai-head{background:#1565c0;color:#fff;padding:12px 16px;font-weight:700;display:flex;
    justify-content:space-between;align-items:center}
  #lai-head small{font-weight:400;opacity:.85;display:block;font-size:11px}
  #lai-body{flex:1;overflow-y:auto;padding:12px;background:#f6f7f6}
  .lai-msg{margin:6px 0;padding:8px 12px;border-radius:12px;max-width:85%;white-space:pre-wrap;
    line-height:1.35;font-size:14px}
  .lai-user{background:#1565c0;color:#fff;margin-left:auto;border-bottom-right-radius:3px}
  .lai-bot{background:#fff;color:#222;border:1px solid #e0e0e0;border-bottom-left-radius:3px}
  .lai-sys{color:#777;font-size:12px;text-align:center;margin:8px 0}
  #lai-suggest{display:flex;flex-wrap:wrap;gap:6px;margin:8px 2px 4px}
  .lai-chip{background:#fff;border:1px solid #1565c0;color:#1565c0;border-radius:14px;
    padding:6px 10px;font-size:12px;cursor:pointer;line-height:1.2;text-align:left}
  .lai-chip:hover{background:#1565c0;color:#fff}
  #lai-foot{display:flex;border-top:1px solid #e0e0e0;padding:8px;gap:6px;background:#fff}
  #lai-input{flex:1;border:1px solid #ccc;border-radius:18px;padding:8px 12px;font-size:14px;outline:none}
  #lai-send{background:#1565c0;color:#fff;border:none;border-radius:18px;padding:0 14px;cursor:pointer;font-weight:600}
  .lai-form{padding:16px}
  .lai-form input{width:100%;box-sizing:border-box;margin:6px 0;padding:9px 12px;border:1px solid #ccc;border-radius:8px;font-size:14px}
  .lai-form button{width:100%;margin-top:8px;background:#1565c0;color:#fff;border:none;border-radius:8px;padding:10px;font-weight:600;cursor:pointer}
  .lai-err{color:#c62828;font-size:13px;margin-top:6px}
  #lai-logout{font-size:11px;cursor:pointer;text-decoration:underline}
  `;
  var style = document.createElement("style");
  style.textContent = css;
  document.head.appendChild(style);

  // ── elementos ────────────────────────────────────────────────────────────────
  var fab = document.createElement("button");
  fab.id = "lai-fab";
  fab.textContent = "LAI";
  document.body.appendChild(fab);

  var panel = document.createElement("div");
  panel.id = "lai-panel";
  panel.innerHTML =
    '<div id="lai-head"><div>LAI<small>Assistente de decisões da lavoura</small></div>' +
    '<div><span id="lai-logout" style="display:none">sair</span> &nbsp;' +
    '<span id="lai-close" style="cursor:pointer">✕</span></div></div>' +
    '<div id="lai-body"></div>';
  document.body.appendChild(panel);

  var body = panel.querySelector("#lai-body");
  var logoutBtn = panel.querySelector("#lai-logout");

  fab.onclick = function () {
    panel.classList.toggle("open");
    if (panel.classList.contains("open")) init();
  };
  panel.querySelector("#lai-close").onclick = function () { panel.classList.remove("open"); };

  function esc(s) { var d = document.createElement("div"); d.textContent = s; return d.innerHTML; }

  function addMsg(text, who) {
    var d = document.createElement("div");
    d.className = "lai-msg " + (who === "user" ? "lai-user" : "lai-bot");
    d.textContent = text;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
    return d;
  }
  function addSys(text) {
    var d = document.createElement("div");
    d.className = "lai-sys";
    d.textContent = text;
    body.appendChild(d);
    body.scrollTop = body.scrollHeight;
  }

  function showLogin(errMsg) {
    logoutBtn.style.display = "none";
    body.innerHTML =
      '<div class="lai-form">' +
      '<p style="font-size:14px;color:#444">Entre para conversar com o LAI sobre as decisões da sua lavoura.</p>' +
      '<input id="lai-email" type="email" placeholder="email" autocomplete="username"/>' +
      '<input id="lai-pass" type="password" placeholder="senha" autocomplete="current-password"/>' +
      '<button id="lai-login-btn">Entrar</button>' +
      (errMsg ? '<div class="lai-err">' + esc(errMsg) + "</div>" : "") +
      "</div>";
    body.querySelector("#lai-login-btn").onclick = doLogin;
    body.querySelector("#lai-pass").onkeydown = function (e) { if (e.key === "Enter") doLogin(); };
  }

  function renderSuggestions() {
    var wrap = document.createElement("div");
    wrap.id = "lai-suggest";
    SUGGESTIONS.forEach(function (q) {
      var chip = document.createElement("button");
      chip.className = "lai-chip";
      chip.textContent = q;
      chip.onclick = function () { send(q); };
      wrap.appendChild(chip);
    });
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  function showChat() {
    logoutBtn.style.display = "inline";
    body.innerHTML = "";
    addSys("Pergunte sobre irrigação, nitrogênio, histórico ou o estado da lavoura. Ou toque numa sugestão:");
    renderSuggestions();
    if (!document.getElementById("lai-foot")) {
      var foot = document.createElement("div");
      foot.id = "lai-foot";
      foot.innerHTML =
        '<input id="lai-input" placeholder="Digite sua pergunta..." autocomplete="off"/>' +
        '<button id="lai-send">➤</button>';
      panel.appendChild(foot);
      foot.querySelector("#lai-send").onclick = send;
      foot.querySelector("#lai-input").onkeydown = function (e) { if (e.key === "Enter") send(); };
    }
    document.getElementById("lai-foot").style.display = "flex";
  }

  function doLogin() {
    var email = body.querySelector("#lai-email").value.trim();
    var pass = body.querySelector("#lai-pass").value;
    if (!email || !pass) return showLogin("Informe email e senha.");
    fetch(API.login, {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin", body: JSON.stringify({ email: email, password: pass }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok) { history = []; showChat(); }
        else showLogin(res.j.error || "Falha no login.");
      })
      .catch(function () { showLogin("Erro de conexão."); });
  }

  function send(preset) {
    var input = document.getElementById("lai-input");
    var text = (typeof preset === "string" ? preset : input.value).trim();
    if (!text) return;
    input.value = "";
    var sug = document.getElementById("lai-suggest");
    if (sug) sug.remove();
    addMsg(text, "user");
    history.push({ role: "user", content: text });
    var thinking = addMsg("…", "bot");
    fetch(API.chat, {
      method: "POST", headers: { "Content-Type": "application/json" },
      credentials: "same-origin", body: JSON.stringify({ message: text, history: history }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, st: r.status, j: j }; }); })
      .then(function (res) {
        if (res.st === 401) { thinking.remove(); return showLogin("Sessão expirada. Entre novamente."); }
        var reply = res.ok ? res.j.reply : (res.j.error || "Erro ao responder.");
        thinking.textContent = reply;
        history.push({ role: "assistant", content: reply });
      })
      .catch(function () { thinking.textContent = "Erro de conexão com o LAI."; });
  }

  logoutBtn.onclick = function () {
    fetch(API.logout, { method: "POST", credentials: "same-origin" }).finally(function () {
      var foot = document.getElementById("lai-foot");
      if (foot) foot.style.display = "none";
      showLogin();
    });
  };

  function init() {
    fetch(API.me, { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (j) { if (j.authenticated) showChat(); else showLogin(); })
      .catch(function () { showLogin(); });
  }
})();
