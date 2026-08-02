/*
 * BotForge embeddable chat widget.
 *
 * Usage (what website owners paste into their HTML):
 *   <script src="https://YOUR-API/widget.js" data-bot-id="THE-BOT-UUID"></script>
 *
 * This script is fully self-contained: it reads its own <script> tag to find the
 * bot id and the API base URL, fetches the bot's widget config, and renders a
 * floating chat bubble + panel inside a Shadow DOM (so the host page's CSS can
 * never leak in and break it, and our styles never leak out). Messages are sent
 * to POST /api/chat/ — the same endpoint the dashboard Test Chat uses.
 */
(function () {
  "use strict";

  // ---- 1. Locate our own <script> tag ------------------------------------
  var script =
    document.currentScript || document.querySelector("script[data-bot-id]");
  if (!script) return;

  var botId = script.getAttribute("data-bot-id");
  if (!botId) {
    console.error("[BotForge] widget.js: missing data-bot-id attribute");
    return;
  }

  // API base = wherever this widget.js was served from, minus the filename.
  var apiBase = script.src.replace(/\/widget\.js.*$/, "");

  // ---- 2. Stable per-visitor identity (persists the conversation) --------
  function persist(key, factory) {
    var v = null;
    try {
      v = localStorage.getItem(key);
    } catch (e) {}
    if (!v && factory) {
      v = factory();
      try {
        localStorage.setItem(key, v);
      } catch (e) {}
    }
    return v;
  }
  var customerId = persist("botforge_cid_" + botId, function () {
    return "web_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
  });
  var conversationId = persist("botforge_conv_" + botId, null);

  // ---- 3. Fetch config, then build the UI --------------------------------
  fetch(apiBase + "/api/widget/" + botId + "/config")
    .then(function (r) {
      if (!r.ok) throw new Error("config request failed: " + r.status);
      return r.json();
    })
    .then(build)
    .catch(function (e) {
      console.error("[BotForge] could not load widget config:", e);
    });

  // ---- 4. Build the widget -----------------------------------------------
  function build(cfg) {
    var primary = cfg.primary_color || "#6366f1";
    var textOn = cfg.text_color || "#ffffff";
    var side = cfg.position === "bottom-left" ? "left" : "right";
    var panelW = Math.min(cfg.width || 380, 420);
    var panelH = cfg.height || 600;
    var greeting = cfg.greeting_message || "Hi! How can I help you today?";
    var botName = cfg.bot_name || "Assistant";

    // Host element + shadow root for full style isolation.
    var host = document.createElement("div");
    host.id = "botforge-widget";
    document.body.appendChild(host);
    var root = host.attachShadow({ mode: "open" });

    var style = document.createElement("style");
    style.textContent = css(primary, textOn, side, panelW, panelH);
    root.appendChild(style);

    // Launcher bubble
    var launcher = el("button", "bf-launcher", root);
    launcher.setAttribute("aria-label", "Open chat");
    launcher.innerHTML = icon("chat");

    // Panel
    var panel = el("div", "bf-panel bf-hidden", root);

    var header = el("div", "bf-header", panel);
    var title = el("div", "bf-title", header);
    title.textContent = botName;
    var closeBtn = el("button", "bf-close", header);
    closeBtn.setAttribute("aria-label", "Close chat");
    closeBtn.innerHTML = icon("close");

    var body = el("div", "bf-body", panel);

    if (cfg.show_powered_by) {
      var pb = el("div", "bf-powered", panel);
      pb.innerHTML = 'Powered by <strong>BotForge</strong>';
    }

    var inputRow = el("form", "bf-input-row", panel);
    var input = el("input", "bf-input", inputRow);
    input.type = "text";
    input.placeholder = "Type a message…";
    input.autocomplete = "off";
    var sendBtn = el("button", "bf-send", inputRow);
    sendBtn.type = "submit";
    sendBtn.setAttribute("aria-label", "Send");
    sendBtn.innerHTML = icon("send");

    // ---- interactions ----
    var opened = false;
    var greeted = false;

    function open() {
      panel.classList.remove("bf-hidden");
      launcher.classList.add("bf-launcher-open");
      opened = true;
      if (!greeted) {
        addMessage("bot", greeting);
        greeted = true;
      }
      setTimeout(function () {
        input.focus();
      }, 50);
    }
    function close() {
      panel.classList.add("bf-hidden");
      launcher.classList.remove("bf-launcher-open");
      opened = false;
    }
    launcher.addEventListener("click", function () {
      opened ? close() : open();
    });
    closeBtn.addEventListener("click", close);

    inputRow.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = input.value.trim();
      if (!text) return;
      input.value = "";
      addMessage("user", text);
      sendMessage(text);
    });

    // Optional auto-open
    if (cfg.auto_open) {
      setTimeout(open, (cfg.auto_open_delay || 5) * 1000);
    }

    // ---- message helpers ----
    function addMessage(who, text) {
      var wrap = el("div", "bf-msg bf-msg-" + who, body);
      var bubble = el("div", "bf-bubble", wrap);
      bubble.textContent = text;
      body.scrollTop = body.scrollHeight;
      return wrap;
    }

    function showTyping() {
      var wrap = el("div", "bf-msg bf-msg-bot bf-typing", body);
      var bubble = el("div", "bf-bubble", wrap);
      bubble.innerHTML = '<span class="bf-dot"></span><span class="bf-dot"></span><span class="bf-dot"></span>';
      body.scrollTop = body.scrollHeight;
      return wrap;
    }

    function sendMessage(text) {
      var typing = showTyping();
      sendBtn.disabled = true;
      fetch(apiBase + "/api/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bot_id: botId,
          message: text,
          conversation_id: conversationId,
          channel: "website",
          customer_id: customerId,
        }),
      })
        .then(function (r) {
          if (!r.ok) throw new Error("chat request failed: " + r.status);
          return r.json();
        })
        .then(function (data) {
          typing.remove();
          sendBtn.disabled = false;
          conversationId = data.conversation_id || conversationId;
          if (conversationId) {
            try {
              localStorage.setItem("botforge_conv_" + botId, conversationId);
            } catch (e) {}
          }
          var content =
            (data.message && data.message.content) ||
            "Sorry, I didn't catch that.";
          addMessage("bot", content);
        })
        .catch(function (e) {
          typing.remove();
          sendBtn.disabled = false;
          addMessage("bot", "Sorry, something went wrong. Please try again.");
          console.error("[BotForge]", e);
        });
    }
  }

  // ---- small DOM helper ----
  function el(tag, className, parent) {
    var e = document.createElement(tag);
    if (className) e.className = className;
    if (parent) parent.appendChild(e);
    return e;
  }

  // ---- inline SVG icons ----
  function icon(name) {
    if (name === "chat") {
      return '<svg viewBox="0 0 24 24" width="26" height="26" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>';
    }
    if (name === "close") {
      return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>';
    }
    // send
    return '<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>';
  }

  // ---- scoped stylesheet ----
  function css(primary, textOn, side, panelW, panelH) {
    return (
      ":host{all:initial;}" +
      "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;}" +
      ".bf-launcher{position:fixed;bottom:20px;" +
      side +
      ":20px;width:60px;height:60px;border-radius:50%;border:none;background:" +
      primary +
      ";color:" +
      textOn +
      ";cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);display:flex;align-items:center;justify-content:center;z-index:2147483000;transition:transform .15s ease;}" +
      ".bf-launcher:hover{transform:scale(1.06);}" +
      ".bf-launcher-open{transform:scale(.9);opacity:.9;}" +
      ".bf-panel{position:fixed;bottom:92px;" +
      side +
      ":20px;width:" +
      panelW +
      "px;max-width:calc(100vw - 40px);height:" +
      panelH +
      "px;max-height:calc(100vh - 120px);background:#fff;border-radius:16px;box-shadow:0 12px 40px rgba(0,0,0,.22);display:flex;flex-direction:column;overflow:hidden;z-index:2147483000;}" +
      ".bf-hidden{display:none;}" +
      ".bf-header{background:" +
      primary +
      ";color:" +
      textOn +
      ";padding:16px 18px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;}" +
      ".bf-title{font-weight:600;font-size:16px;}" +
      ".bf-close{background:transparent;border:none;color:" +
      textOn +
      ";cursor:pointer;opacity:.85;padding:0;display:flex;}" +
      ".bf-close:hover{opacity:1;}" +
      ".bf-body{flex:1;overflow-y:auto;padding:16px;background:#f7f8fa;display:flex;flex-direction:column;gap:10px;}" +
      ".bf-msg{display:flex;max-width:85%;}" +
      ".bf-msg-user{align-self:flex-end;}" +
      ".bf-msg-bot{align-self:flex-start;}" +
      ".bf-bubble{padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.45;white-space:pre-wrap;word-wrap:break-word;}" +
      ".bf-msg-user .bf-bubble{background:" +
      primary +
      ";color:" +
      textOn +
      ";border-bottom-right-radius:4px;}" +
      ".bf-msg-bot .bf-bubble{background:#fff;color:#1f2430;border:1px solid #e6e8ec;border-bottom-left-radius:4px;}" +
      ".bf-typing .bf-bubble{display:flex;gap:4px;align-items:center;}" +
      ".bf-dot{width:7px;height:7px;border-radius:50%;background:#b6bcc6;animation:bf-blink 1.2s infinite both;}" +
      ".bf-dot:nth-child(2){animation-delay:.2s;}" +
      ".bf-dot:nth-child(3){animation-delay:.4s;}" +
      "@keyframes bf-blink{0%,80%,100%{opacity:.3;}40%{opacity:1;}}" +
      ".bf-powered{text-align:center;font-size:11px;color:#9aa1ac;padding:6px;background:#f7f8fa;flex-shrink:0;}" +
      ".bf-powered strong{color:#6b7280;}" +
      ".bf-input-row{display:flex;gap:8px;padding:12px;border-top:1px solid #eceef1;background:#fff;flex-shrink:0;}" +
      ".bf-input{flex:1;border:1px solid #d7dae0;border-radius:10px;padding:10px 12px;font-size:14px;outline:none;}" +
      ".bf-input:focus{border-color:" +
      primary +
      ";}" +
      ".bf-send{border:none;background:" +
      primary +
      ";color:" +
      textOn +
      ";width:40px;border-radius:10px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;}" +
      ".bf-send:disabled{opacity:.5;cursor:default;}"
    );
  }
})();
