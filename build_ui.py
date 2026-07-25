html = r"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sandra AI - Voice Assistant</title>
    <meta name="description" content="Sandra AI - Voice assistant powered by Gemini Live API">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <style>
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        :root {
            --bg: #080808;
            --surface: rgba(255,255,255,0.04);
            --border: rgba(255,255,255,0.08);
            --text: #f0f0f0;
            --muted: #6b7280;
            --accent: #7c6dfa;
            --accent-glow: rgba(124,109,250,0.4);
            --green: #22c55e;
            --green-glow: rgba(34,197,94,0.35);
            --red: #ef4444;
            --red-glow: rgba(239,68,68,0.3);
            --font: 'Inter', -apple-system, sans-serif;
            --mono: 'JetBrains Mono', monospace;
        }
        html, body { height: 100%; background: var(--bg); color: var(--text); font-family: var(--font); overflow: hidden; }

        /* NAV */
        .nav {
            position: fixed; top: 0; left: 0; right: 0; height: 64px;
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 2rem; z-index: 100;
            background: rgba(8,8,8,0.75); backdrop-filter: blur(24px);
            border-bottom: 1px solid var(--border);
        }
        .nav-logo { display: flex; align-items: center; gap: 0.6rem; }
        .nav-logo-mark {
            width: 32px; height: 32px; border-radius: 9px;
            background: var(--accent); display: flex; align-items: center;
            justify-content: center; font-size: 0.9rem; font-weight: 700; color: #fff;
            box-shadow: 0 0 18px var(--accent-glow);
        }
        .nav-logo-name { font-size: 1rem; font-weight: 600; letter-spacing: -0.02em; }
        .status-pill {
            display: flex; align-items: center; gap: 0.5rem;
            padding: 0.4rem 1rem; border-radius: 99px;
            background: var(--surface); border: 1px solid var(--border);
            font-size: 0.8rem; font-weight: 500; color: var(--muted);
        }
        .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--muted); flex-shrink: 0; }
        .dot.live { background: var(--green); box-shadow: 0 0 10px var(--green-glow); animation: blink 1.6s infinite; }
        .dot.speaking { background: var(--accent); box-shadow: 0 0 10px var(--accent-glow); animation: blink 1.2s infinite; }
        .dot.muted { background: var(--red); }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.35} }
        .nav-right { display: flex; align-items: center; gap: 0.75rem; }
        .nav-btn {
            display: flex; align-items: center; gap: 0.45rem;
            padding: 0.42rem 0.9rem; border-radius: 8px;
            background: var(--surface); border: 1px solid var(--border);
            color: var(--muted); font-family: var(--font); font-size: 0.8rem;
            font-weight: 500; cursor: pointer; transition: all 0.18s;
        }
        .nav-btn:hover { background: rgba(255,255,255,0.08); color: var(--text); border-color: rgba(255,255,255,0.15); }
        .voice-select {
            background: var(--surface); border: 1px solid var(--border);
            color: var(--text); font-family: var(--font); font-size: 0.8rem;
            font-weight: 500; padding: 0.42rem 0.9rem; border-radius: 8px; outline: none; cursor: pointer;
        }
        .voice-select option { background: #111; }
        .profile-menu { position: relative; }
        .profile-trigger {
            display: flex; align-items: center; gap: 0.5rem;
            padding: 0.35rem 0.85rem; border-radius: 8px;
            background: var(--surface); border: 1px solid var(--border);
            cursor: pointer; font-size: 0.8rem; font-weight: 500;
            color: var(--muted); transition: all 0.18s;
        }
        .profile-trigger:hover { background: rgba(255,255,255,0.08); color: var(--text); }
        .avatar {
            width: 24px; height: 24px; border-radius: 50%;
            background: var(--accent); display: flex; align-items: center;
            justify-content: center; font-size: 0.72rem; font-weight: 700; color: #fff;
        }
        .profile-dropdown {
            display: none; position: absolute; top: calc(100% + 10px); right: 0;
            min-width: 240px; background: rgba(12,12,14,0.98);
            backdrop-filter: blur(30px); border: 1px solid var(--border);
            border-radius: 14px; padding: 1rem;
            box-shadow: 0 20px 50px rgba(0,0,0,0.6); z-index: 200;
        }
        .profile-menu.open .profile-dropdown { display: block; }
        .p-info { margin-bottom: 0.75rem; padding-bottom: 0.75rem; border-bottom: 1px solid var(--border); }
        .p-label { font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); margin-bottom: 0.3rem; }
        .p-email { font-size: 0.88rem; font-weight: 600; word-break: break-all; }
        .p-phone { font-size: 0.78rem; color: var(--muted); font-family: var(--mono); margin-top: 0.2rem; }
        .p-btn {
            display: flex; align-items: center; justify-content: center; gap: 0.4rem;
            width: 100%; padding: 0.6rem; border-radius: 8px;
            background: var(--surface); border: 1px solid var(--border);
            color: var(--text); font-family: var(--font); font-size: 0.82rem;
            font-weight: 500; cursor: pointer; margin-top: 0.5rem; transition: all 0.18s;
        }
        .p-btn:hover { background: rgba(255,255,255,0.08); }
        .p-btn.danger { color: var(--red); }
        .p-btn.danger:hover { background: rgba(239,68,68,0.08); }

        /* STAGE */
        .stage {
            height: 100vh; display: flex; flex-direction: column;
            align-items: center; justify-content: center;
            padding: 64px 2rem 80px; gap: 0;
        }
        .agent-label {
            font-size: 0.7rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.22em; color: var(--muted); margin-bottom: 2.5rem;
            opacity: 0; animation: fadeUp 0.8s 0.3s ease forwards;
        }
        @keyframes fadeUp { from{opacity:0;transform:translateY(12px)} to{opacity:1;transform:none} }

        /* ORB */
        .orb-wrap {
            position: relative; width: 280px; height: 280px;
            display: flex; align-items: center; justify-content: center;
            margin-bottom: 2.25rem;
        }
        .orb-ring {
            position: absolute; inset: -22px; border-radius: 50%;
            border: 1px solid rgba(124,109,250,0.1);
            animation: breathe 4s ease-in-out infinite;
        }
        .orb-ring-2 {
            position: absolute; inset: -44px; border-radius: 50%;
            border: 1px solid rgba(124,109,250,0.05);
            animation: breathe 4s ease-in-out 1s infinite;
        }
        @keyframes breathe { 0%,100%{transform:scale(1);opacity:.5} 50%{transform:scale(1.05);opacity:1} }
        #orbCanvas { width: 280px; height: 280px; border-radius: 50%; position: relative; z-index: 2; }
        .orb-glow {
            position: absolute; inset: 12%; border-radius: 50%;
            background: radial-gradient(circle, var(--accent-glow) 0%, transparent 70%);
            filter: blur(28px); z-index: 1; transition: opacity 0.6s;
        }

        /* TITLE */
        .orb-title {
            font-size: 2.1rem; font-weight: 300; letter-spacing: -0.035em;
            text-align: center; margin-bottom: 0.5rem;
            opacity: 0; animation: fadeUp 0.8s 0.55s ease forwards;
        }
        .orb-title strong { font-weight: 700; }
        .orb-sub {
            font-size: 0.9rem; color: var(--muted); text-align: center;
            margin-bottom: 2.5rem;
            opacity: 0; animation: fadeUp 0.8s 0.7s ease forwards;
        }

        /* CALL BUTTON */
        .call-btn {
            display: flex; align-items: center; gap: 0.75rem;
            padding: 0.9rem 2.4rem; border-radius: 99px;
            background: #fff; color: #080808; border: none;
            font-family: var(--font); font-size: 0.95rem; font-weight: 600;
            cursor: pointer; letter-spacing: -0.01em;
            box-shadow: 0 4px 28px rgba(255,255,255,0.14), 0 1px 4px rgba(0,0,0,0.4);
            transition: all 0.25s cubic-bezier(0.16,1,0.3,1);
            position: relative; overflow: hidden;
            opacity: 0; animation: fadeUp 0.8s 0.85s ease forwards;
        }
        .call-btn::before {
            content: ""; position: absolute; inset: 0;
            background: linear-gradient(135deg,rgba(255,255,255,0.16) 0%,transparent 60%);
            pointer-events: none;
        }
        .call-btn:hover { transform: translateY(-2px) scale(1.02); box-shadow: 0 8px 36px rgba(255,255,255,0.2); }
        .call-btn:active { transform: scale(0.98); }
        .call-btn.active {
            background: #141414; color: var(--red);
            border: 1px solid rgba(239,68,68,0.3);
            box-shadow: 0 0 32px rgba(239,68,68,0.25);
        }
        .call-icon { width: 18px; height: 18px; flex-shrink: 0; }

        /* PEEK BUTTON */
        .peek-btn {
            position: fixed; bottom: 1.75rem; left: 50%; transform: translateX(-50%);
            display: flex; align-items: center; gap: 0.5rem;
            padding: 0.55rem 1.4rem; border-radius: 99px;
            background: rgba(255,255,255,0.05); border: 1px solid var(--border);
            color: var(--muted); font-family: var(--font); font-size: 0.78rem;
            font-weight: 500; cursor: pointer; transition: all 0.18s;
            z-index: 50; backdrop-filter: blur(12px);
            opacity: 0; animation: fadeUp 0.8s 1s ease forwards;
        }
        .peek-btn:hover { background: rgba(255,255,255,0.09); color: var(--text); border-color: rgba(255,255,255,0.16); }
        .peek-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 8px var(--accent-glow); }

        /* CHAT DRAWER */
        .drawer {
            position: fixed; bottom: -540px; left: 50%;
            transform: translateX(-50%); width: min(740px, 94vw); height: 540px;
            background: rgba(9,9,11,0.94); backdrop-filter: blur(40px) saturate(160%);
            border: 1px solid var(--border); border-bottom: none;
            border-radius: 24px 24px 0 0;
            display: flex; flex-direction: column;
            z-index: 300; transition: bottom 0.5s cubic-bezier(0.16,1,0.3,1);
            box-shadow: 0 -16px 60px rgba(0,0,0,0.5);
        }
        .drawer.open { bottom: 0; }
        .drawer-handle-area {
            height: 36px; display: flex; align-items: center;
            justify-content: center; cursor: pointer; flex-shrink: 0;
        }
        .drawer-handle {
            width: 40px; height: 4px; border-radius: 99px;
            background: rgba(255,255,255,0.1); transition: width 0.2s, background 0.2s;
        }
        .drawer-handle-area:hover .drawer-handle { width: 60px; background: rgba(255,255,255,0.22); }
        .drawer-header {
            display: flex; align-items: center; justify-content: space-between;
            padding: 0 1.5rem 0.75rem; border-bottom: 1px solid var(--border); flex-shrink: 0;
        }
        .drawer-title {
            display: flex; align-items: center; gap: 0.5rem;
            font-size: 0.72rem; font-weight: 600; text-transform: uppercase;
            letter-spacing: 0.1em; color: var(--muted);
        }
        .drawer-close {
            background: none; border: none; color: var(--muted);
            font-size: 1.3rem; cursor: pointer; transition: color 0.18s; line-height: 1;
        }
        .drawer-close:hover { color: var(--text); }
        .transcript {
            flex: 1; overflow-y: auto; padding: 1.25rem 1.5rem;
            display: flex; flex-direction: column; gap: 0.85rem;
        }
        .transcript::-webkit-scrollbar { width: 3px; }
        .transcript::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.07); border-radius: 99px; }
        .msg {
            font-size: 0.9rem; line-height: 1.55; padding: 0.75rem 1.1rem;
            border-radius: 16px; max-width: 78%; word-wrap: break-word;
            animation: msgPop 0.28s cubic-bezier(0.34,1.56,0.64,1);
        }
        @keyframes msgPop { from{opacity:0;transform:translateY(8px) scale(0.97)} to{opacity:1;transform:none} }
        .msg.user { align-self: flex-end; background: rgba(124,109,250,0.1); border: 1px solid rgba(124,109,250,0.2); border-bottom-right-radius: 4px; }
        .msg.ai { align-self: flex-start; background: rgba(255,255,255,0.04); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
        .msg.system { align-self: center; background: transparent; border: none; color: var(--muted); font-size: 0.78rem; padding: 0.25rem 0; max-width: 100%; text-align: center; }
        .msg.tool { align-self: center; background: rgba(34,197,94,0.04); border: 1px solid rgba(34,197,94,0.15); border-left: 3px solid var(--green); color: var(--green); font-family: var(--mono); font-size: 0.78rem; border-radius: 10px; max-width: 90%; white-space: pre-wrap; line-height: 1.5; }
        .chat-bar { display: flex; gap: 0.75rem; padding: 0.75rem 1.25rem 1.2rem; flex-shrink: 0; }
        .chat-input {
            flex: 1; background: rgba(255,255,255,0.04); border: 1px solid var(--border);
            border-radius: 12px; padding: 0.7rem 1.1rem; color: var(--text);
            font-family: var(--font); font-size: 0.88rem; outline: none; transition: border-color 0.18s;
        }
        .chat-input:focus { border-color: rgba(124,109,250,0.45); }
        .chat-input::placeholder { color: var(--muted); }
        .chat-input:disabled { opacity: 0.35; cursor: not-allowed; }
        .btn-send {
            background: var(--accent); border: none; color: #fff;
            padding: 0.7rem 1.4rem; border-radius: 12px;
            font-family: var(--font); font-size: 0.88rem; font-weight: 600;
            cursor: pointer; transition: all 0.18s; box-shadow: 0 4px 14px var(--accent-glow);
        }
        .btn-send:hover { transform: translateY(-1px); box-shadow: 0 6px 20px var(--accent-glow); }
        .btn-send:disabled { opacity: 0.3; cursor: not-allowed; transform: none; box-shadow: none; }

        /* HISTORY DRAWER */
        .history-drawer {
            position: fixed; top: 0; right: -380px; width: 360px; height: 100vh;
            background: rgba(9,9,11,0.96); backdrop-filter: blur(40px);
            border-left: 1px solid var(--border);
            display: flex; flex-direction: column; padding: 2rem 1.5rem;
            z-index: 400; transition: right 0.4s cubic-bezier(0.16,1,0.3,1);
            box-shadow: -10px 0 50px rgba(0,0,0,0.5);
        }
        .history-drawer.open { right: 0; }
        .history-hdr { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem; }
        .history-title { font-size: 0.85rem; font-weight: 600; letter-spacing: -0.01em; }
        .history-close { background: none; border: none; color: var(--muted); font-size: 1.3rem; cursor: pointer; transition: color 0.18s; }
        .history-close:hover { color: var(--text); }
        .history-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 0.6rem; }
        .history-list::-webkit-scrollbar { width: 3px; }
        .history-list::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.06); border-radius: 99px; }
        .history-item {
            padding: 0.85rem 1rem; border-radius: 12px;
            background: var(--surface); border: 1px solid var(--border);
            cursor: pointer; transition: all 0.18s;
        }
        .history-item:hover { background: rgba(255,255,255,0.07); border-color: rgba(255,255,255,0.15); transform: translateX(4px); }
        .h-time { font-size: 0.7rem; color: var(--muted); font-family: var(--mono); margin-bottom: 0.2rem; }
        .h-id { font-size: 0.85rem; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

        /* AUTH MODAL */
        .modal-overlay {
            position: fixed; inset: 0; background: rgba(0,0,0,0.85);
            backdrop-filter: blur(24px); display: flex; align-items: center;
            justify-content: center; z-index: 500;
        }
        .modal {
            background: rgba(11,11,13,0.97); border: 1px solid var(--border);
            border-radius: 24px; padding: 2.75rem 2.5rem; width: min(440px,92vw);
            position: relative; overflow: hidden;
            box-shadow: 0 40px 80px rgba(0,0,0,0.7);
        }
        .modal::before { content: ""; position: absolute; top:0;left:0;right:0;height:3px; background: linear-gradient(90deg,var(--accent),#a78bfa); }
        .modal-logo { display: flex; align-items: center; gap: 0.6rem; margin-bottom: 1.75rem; }
        .modal-logo-mark { width:36px;height:36px;border-radius:10px;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:1rem;font-weight:700;color:#fff;box-shadow:0 0 20px var(--accent-glow); }
        .modal-logo-name { font-size: 1.1rem; font-weight: 600; }
        .modal-tabs { display:flex;gap:0;margin-bottom:1.75rem;background:rgba(255,255,255,0.04);border-radius:10px;padding:3px; }
        .modal-tab { flex:1;padding:0.5rem;border-radius:8px;border:none;background:transparent;color:var(--muted);font-family:var(--font);font-size:0.85rem;font-weight:500;cursor:pointer;transition:all 0.18s; }
        .modal-tab.active { background:rgba(255,255,255,0.08);color:var(--text); }
        .modal-input { width:100%;background:rgba(255,255,255,0.04);border:1px solid var(--border);border-radius:12px;padding:0.85rem 1.1rem;color:var(--text);font-family:var(--font);font-size:0.9rem;outline:none;margin-bottom:0.85rem;transition:border-color 0.18s,box-shadow 0.18s; }
        .modal-input:focus { border-color:rgba(124,109,250,0.5);box-shadow:0 0 0 3px rgba(124,109,250,0.08); }
        .modal-input::placeholder { color:var(--muted); }
        .modal-submit { width:100%;background:#fff;color:#080808;border:none;padding:0.9rem;border-radius:12px;font-family:var(--font);font-size:0.92rem;font-weight:600;cursor:pointer;transition:all 0.18s;margin-top:0.25rem;box-shadow:0 4px 20px rgba(255,255,255,0.1); }
        .modal-submit:hover { background:#f0f0f0;transform:translateY(-1px); }
        .net-alert { position:fixed;top:80px;left:50%;transform:translateX(-50%);background:rgba(239,68,68,0.92);color:#fff;padding:0.75rem 1.5rem;border-radius:12px;display:flex;align-items:center;gap:1rem;font-size:0.85rem;font-weight:500;z-index:600;box-shadow:0 10px 30px rgba(239,68,68,0.3);backdrop-filter:blur(10px); }
        .net-btn { background:#fff;color:var(--red);border:none;padding:0.4rem 0.9rem;border-radius:7px;font-size:0.82rem;font-weight:600;cursor:pointer; }
        .hidden { display:none!important; }
    </style>
</head>
<body>

<!-- NETWORK ALERT -->
<div id="networkAlert" class="net-alert hidden">
    <span>Connection lost. Switch to cellular?</span>
    <button id="triggerCellularBtn" class="net-btn">Dial Now</button>
</div>

<!-- AUTH MODAL -->
<div id="authModal" class="modal-overlay">
    <div class="modal">
        <div class="modal-logo">
            <div class="modal-logo-mark">S</div>
            <span class="modal-logo-name">Sandra AI</span>
        </div>
        <div class="modal-tabs">
            <button id="tabLogin" class="modal-tab active" onclick="switchTab('login')">Log In</button>
            <button id="tabRegister" class="modal-tab" onclick="switchTab('register')">Register</button>
        </div>
        <form id="authForm" onsubmit="handleAuthSubmit(event)">
            <input type="email" id="authEmail" class="modal-input" placeholder="Email" required>
            <input type="password" id="authPassword" class="modal-input" placeholder="Password" required>
            <input type="tel" id="authPhone" class="modal-input hidden" placeholder="Phone (e.g. +15550199)">
            <input type="password" id="geminiKey" class="modal-input" placeholder="Gemini API Key" required>
            <button type="submit" id="authActionBtn" class="modal-submit">Log In</button>
        </form>
    </div>
</div>

<!-- NAV -->
<header class="nav">
    <div class="nav-logo">
        <div class="nav-logo-mark">S</div>
        <span class="nav-logo-name">Sandra AI</span>
    </div>
    <div class="status-pill">
        <div class="dot" id="statusDot"></div>
        <span id="statusText">Disconnected</span>
    </div>
    <div class="nav-right">
        <select id="voiceConfig" class="voice-select">
            <option value="Aoede">Aoede</option>
            <option value="Kore">Kore</option>
            <option value="Puck">Puck</option>
            <option value="Charon" selected>Charon</option>
            <option value="Fenrir">Fenrir</option>
        </select>
        <button class="nav-btn" id="openDrawerBtn">History</button>
        <div class="profile-menu" id="profileMenu">
            <div class="profile-trigger" id="profileTrigger">
                <div class="avatar" id="avatarLetter">U</div>
                <span id="profileTriggerEmail">Account</span>
            </div>
            <div class="profile-dropdown">
                <div class="p-info">
                    <div class="p-label">Signed in as</div>
                    <div class="p-email" id="profileEmail">Not authenticated</div>
                    <div class="p-phone" id="profilePhoneVal">-</div>
                </div>
                <button id="googleAuthBtn" class="p-btn">Sync Google Calendar</button>
                <button class="p-btn danger" onclick="logout()">Log Out</button>
            </div>
        </div>
    </div>
</header>

<!-- MAIN -->
<main class="stage">
    <div class="agent-label">Sandra AI &nbsp;&bull;&nbsp; Voice Agent</div>
    <div class="orb-wrap" id="orbWrap">
        <div class="orb-ring"></div>
        <div class="orb-ring-2"></div>
        <div class="orb-glow" id="orbGlow"></div>
        <canvas id="orbCanvas" width="280" height="280"></canvas>
    </div>
    <p class="orb-title"><strong>Talk</strong> to Sandra</p>
    <p class="orb-sub">Your intelligent voice assistant, always listening.</p>
    <select id="audioSource" style="display:none"><option>Loading...</option></select>
    <input type="hidden" id="phoneConfig">
    <button class="call-btn" id="callBtn">
        <svg class="call-icon" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2c1.1 0 2 .9 2 2v8c0 1.1-.9 2-2 2s-2-.9-2-2V4c0-1.1.9-2 2-2zm6 10c0 3.31-2.69 6-6 6s-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8h-2z"/>
        </svg>
        <span id="callBtnText">Start Session</span>
    </button>
</main>

<!-- PEEK BUTTON -->
<button class="peek-btn" id="openTranscriptBtn">
    <div class="peek-dot"></div>
    Transcript &amp; Chat &#8593;
</button>

<!-- CHAT DRAWER -->
<div class="drawer" id="chatDrawer">
    <div class="drawer-handle-area" id="drawerHandle"><div class="drawer-handle"></div></div>
    <div class="drawer-header">
        <div class="drawer-title"><div class="peek-dot"></div>&nbsp;Live Transcript</div>
        <button class="drawer-close" id="closeDrawerBtn">&times;</button>
    </div>
    <div class="transcript" id="transcript"><div class="msg system">Log in to start a session.</div></div>
    <div class="chat-bar">
        <input type="text" id="chatInput" class="chat-input" placeholder="Connect a call to type..." disabled>
        <button id="sendTextBtn" class="btn-send" disabled>Send</button>
    </div>
</div>

<!-- HISTORY DRAWER -->
<div class="history-drawer" id="historyDrawer">
    <div class="history-hdr">
        <span class="history-title">Call History</span>
        <button class="history-close" id="closeHistoryBtn">&times;</button>
    </div>
    <div class="history-list" id="historyList"><div class="msg system" style="padding:0">No calls yet.</div></div>
</div>

<script>
const UI = {
    authModal: document.getElementById('authModal'),
    authEmail: document.getElementById('authEmail'),
    authPassword: document.getElementById('authPassword'),
    authPhone: document.getElementById('authPhone'),
    geminiKey: document.getElementById('geminiKey'),
    authActionBtn: document.getElementById('authActionBtn'),
    profileEmail: document.getElementById('profileEmail'),
    profilePhoneVal: document.getElementById('profilePhoneVal'),
    statusText: document.getElementById('statusText'),
    statusDot: document.getElementById('statusDot'),
    transcript: document.getElementById('transcript'),
    callBtn: document.getElementById('callBtn'),
    callBtnText: document.getElementById('callBtnText'),
    audioSource: document.getElementById('audioSource'),
    voiceConfig: document.getElementById('voiceConfig'),
    phoneConfig: document.getElementById('phoneConfig'),
    networkAlert: document.getElementById('networkAlert'),
    triggerCellularBtn: document.getElementById('triggerCellularBtn'),
    chatInput: document.getElementById('chatInput'),
    sendTextBtn: document.getElementById('sendTextBtn'),
    chatDrawer: document.getElementById('chatDrawer'),
    historyList: document.getElementById('historyList'),
    orbGlow: document.getElementById('orbGlow'),
    orbCanvas: document.getElementById('orbCanvas'),
};

let currentUser=null, isCallActive=false, ws=null, audioContext=null, mediaStream=null, audioWorkletNode=null;
let nextPlayTime=0, sessionId='', userMsgBuf='', aiMsgBuf='', activeBubble=null, activeRole=null;
let activeSources=[], micAnalyser=null, aiAnalyser=null, recognition=null, phase=0, activeTab='login';

function switchTab(t) {
    activeTab = t;
    document.getElementById('tabLogin').classList.toggle('active', t==='login');
    document.getElementById('tabRegister').classList.toggle('active', t==='register');
    UI.authActionBtn.textContent = t==='login' ? 'Log In' : 'Create Account';
    UI.authPhone.classList.toggle('hidden', t==='login');
}

async function handleAuthSubmit(e) {
    e.preventDefault();
    const email=UI.authEmail.value.trim(), password=UI.authPassword.value.trim();
    const phone=UI.authPhone.value.trim(), apiKey=UI.geminiKey.value.trim();
    if (!apiKey) return alert('Gemini API Key required.');
    localStorage.setItem('gemini_api_key', apiKey);
    const ep = activeTab==='login' ? '/api/login' : '/api/register';
    const body = activeTab==='login' ? {email,password} : {email,password,phone_number:phone};
    try {
        const res = await fetch('http://127.0.0.1:5000'+ep, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const data = await res.json();
        if (data.error) return alert(data.error);
        currentUser = data.user;
        localStorage.setItem('user', JSON.stringify(currentUser));
        UI.authModal.classList.add('hidden');
        loadUserProfile();
    } catch(err) { alert('Auth failed: '+err); }
}

function loadUserProfile() {
    if (!currentUser) return;
    UI.profileEmail.textContent = currentUser.email;
    UI.profilePhoneVal.textContent = currentUser.phone_number || '-';
    UI.phoneConfig.value = currentUser.phone_number || '';
    const el = document.getElementById('profileTriggerEmail');
    if (el) el.textContent = currentUser.email.split('@')[0];
    const av = document.getElementById('avatarLetter');
    if (av) av.textContent = currentUser.email.charAt(0).toUpperCase();
    updateStatus('Ready', '');
    addMsg('Session ready. Press Start to connect.', 'system');
    fetchHistory();
}

function logout() {
    localStorage.clear(); currentUser = null;
    UI.authModal.classList.remove('hidden');
    UI.profileEmail.textContent = 'Not authenticated';
    UI.profilePhoneVal.textContent = '-';
    document.getElementById('profileTriggerEmail').textContent = 'Account';
    document.getElementById('avatarLetter').textContent = 'U';
    UI.historyList.innerHTML = "<div class='msg system' style='padding:0'>No calls yet.</div>";
    UI.transcript.innerHTML = "<div class='msg system'>Log in to start a session.</div>";
    if (isCallActive) stopCall();
}

function updateStatus(txt, cls) {
    UI.statusText.textContent = txt;
    UI.statusDot.className = 'dot' + (cls ? ' '+cls : '');
}

function addMsg(text, type='system', chunk=false) {
    if (chunk) {
        if (activeBubble && activeRole===type) {
            activeBubble.textContent += text;
            if (type==='user') userMsgBuf += text;
            if (type==='ai') aiMsgBuf += text;
            UI.transcript.scrollTop = UI.transcript.scrollHeight;
            return;
        }
        flushBufs();
        activeBubble = document.createElement('div');
        activeBubble.className = 'msg '+type;
        activeBubble.textContent = text;
        if (type==='user') userMsgBuf = text;
        if (type==='ai') aiMsgBuf = text;
        UI.transcript.appendChild(activeBubble);
        activeRole = type;
    } else {
        flushBufs();
        const el = document.createElement('div');
        el.className = 'msg '+type; el.textContent = text;
        UI.transcript.appendChild(el);
        activeBubble = null; activeRole = null;
    }
    UI.transcript.scrollTop = UI.transcript.scrollHeight;
}

function addTool(text) {
    flushBufs();
    const el = document.createElement('div');
    el.className = 'msg tool'; el.textContent = text;
    UI.transcript.appendChild(el);
    UI.transcript.scrollTop = UI.transcript.scrollHeight;
    activeBubble = null; activeRole = null;
}

function flushBufs() {
    if (activeRole==='user' && userMsgBuf.trim()) { logConv('user', userMsgBuf); userMsgBuf=''; }
    if (activeRole==='ai' && aiMsgBuf.trim()) { logConv('assistant', aiMsgBuf); aiMsgBuf=''; }
}

async function logConv(speaker, text) {
    if (!sessionId || !text.trim() || !currentUser) return;
    try { await fetch('http://127.0.0.1:5000/api/log_conversation', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,speaker,text,user_id:currentUser.id})}); }
    catch(e) { console.error(e); }
}

async function fetchHistory() {
    if (!currentUser) return;
    try {
        const res = await fetch('http://127.0.0.1:5000/api/history?user_id='+currentUser.id);
        const hist = await res.json();
        UI.historyList.innerHTML = '';
        if (!hist.length) { UI.historyList.innerHTML = "<div class='msg system' style='padding:0'>No calls yet.</div>"; return; }
        hist.forEach(s => {
            const el = document.createElement('div'); el.className = 'history-item';
            el.innerHTML = "<div class='h-time'>"+new Date(s.timestamp).toLocaleString()+"</div><div class='h-id'>"+s.session_id+"</div>";
            el.addEventListener('click', () => fetchSessionChat(s.session_id));
            UI.historyList.appendChild(el);
        });
    } catch(e) { console.error(e); }
}

async function fetchSessionChat(sId) {
    try {
        const res = await fetch('http://127.0.0.1:5000/api/history/session?session_id='+sId);
        const chat = await res.json();
        UI.transcript.innerHTML = "<div class='msg system'>Past call: "+sId+"</div>";
        chat.forEach(t => addMsg(t[1], t[0]==='user' ? 'user' : 'ai', false));
        document.getElementById('historyDrawer').classList.remove('open');
        UI.chatDrawer.classList.add('open');
    } catch(e) { console.error(e); }
}

async function enumerateMics() {
    try {
        await navigator.mediaDevices.getUserMedia({audio:true});
        const devs = await navigator.mediaDevices.enumerateDevices();
        UI.audioSource.innerHTML = '';
        devs.filter(d=>d.kind==='audioinput').forEach((d,i) => {
            const o = document.createElement('option');
            o.value = d.deviceId; o.text = d.label || 'Microphone '+(i+1);
            UI.audioSource.appendChild(o);
        });
    } catch(e) { UI.audioSource.innerHTML = '<option>Permission denied</option>'; }
}

function startSR() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) return;
    recognition = new SR();
    recognition.continuous = true; recognition.interimResults = true; recognition.lang = 'en-US';
    recognition.onresult = e => {
        let f='', it='';
        for (let i=e.resultIndex; i<e.results.length; i++) {
            if (e.results[i].isFinal) f += e.results[i][0].transcript;
            else it += e.results[i][0].transcript;
        }
        if (f||it) UI.chatInput.value = f||it;
    };
    recognition.onerror = e => console.error(e);
    recognition.start();
}

function stopSR() { if (recognition) { recognition.stop(); recognition = null; } }

UI.callBtn.addEventListener('click', async () => {
    if (!currentUser) return alert('Please log in first.');
    isCallActive = !isCallActive;
    if (isCallActive) {
        sessionId = 'session_'+Date.now();
        UI.callBtn.classList.add('active');
        UI.callBtnText.textContent = 'End Session';
        UI.chatDrawer.classList.add('open');
        updateStatus('Listening...', 'live');
        addMsg('Connecting to voice agent...', 'system');
        const key = localStorage.getItem('gemini_api_key');
        const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        ws = new WebSocket(wsProto + '//' + window.location.host + '/ws?user_id=' + currentUser.id + '&key=' + key);
        let pingTimer = null;
        ws.onopen = async () => {
            pingTimer = setInterval(() => { if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ping:true})); }, 15000);
            let mem = 'No past memory found.';
            try { const r = await fetch('http://127.0.0.1:5000/api/get_memory?user_id='+currentUser.id); const d = await r.json(); mem = d.context; }
            catch(e) { console.error(e); }
            const dt = new Date().toString(), tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
            const sp = 'You are Sandra, a premium AI voice assistant.\nToday: '+dt+'. Timezone: '+tz+'.\n'+mem+'\nTools: update_user_memory, send_email, add_todo, check_availability, book_meeting, web_search.';
            ws.send(JSON.stringify({setup:{
                model:'models/gemini-3.1-flash-live-preview',
                generationConfig:{responseModalities:['AUDIO'],speechConfig:{voiceConfig:{prebuiltVoiceConfig:{voiceName:UI.voiceConfig.value}}},thinkingConfig:{thinkingLevel:'MINIMAL'}},
                systemInstruction:{parts:[{text:sp}]},
                tools:[{functionDeclarations:[
                    {name:'check_availability',description:'Check calendar availability.',parameters:{type:'OBJECT',properties:{date:{type:'STRING'},timezone:{type:'STRING'}},required:['date']}},
                    {name:'book_meeting',description:'Book a meeting.',parameters:{type:'OBJECT',properties:{title:{type:'STRING'},date_time:{type:'STRING'},guest_email:{type:'STRING'},guest_emails:{type:'STRING'},duration:{type:'INTEGER'},timezone:{type:'STRING'}},required:['title','date_time','guest_email']}},
                    {name:'update_user_memory',description:'Save user info.',parameters:{type:'OBJECT',properties:{key:{type:'STRING'},value:{type:'STRING'}},required:['key','value']}},
                    {name:'send_email',description:'Send email.',parameters:{type:'OBJECT',properties:{to:{type:'STRING'},subject:{type:'STRING'},body:{type:'STRING'}},required:['to','subject','body']}},
                    {name:'add_todo',description:'Add task.',parameters:{type:'OBJECT',properties:{title:{type:'STRING'},notes:{type:'STRING'},due:{type:'STRING'}},required:['title']}},
                    {name:'web_search',description:'Web search.',parameters:{type:'OBJECT',properties:{query:{type:'STRING'}},required:['query']}}
                ]}]
            }}));
            audioContext = new AudioContext({sampleRate:16000});
            micAnalyser = audioContext.createAnalyser(); micAnalyser.fftSize = 256;
            aiAnalyser = audioContext.createAnalyser(); aiAnalyser.fftSize = 256;
            mediaStream = await navigator.mediaDevices.getUserMedia({audio:{deviceId:UI.audioSource.value?{exact:UI.audioSource.value}:undefined,sampleRate:16000,channelCount:1}});
            const src = audioContext.createMediaStreamSource(mediaStream);
            src.connect(micAnalyser);
            await audioContext.audioWorklet.addModule(URL.createObjectURL(new Blob(["class PCMProcessor extends AudioWorkletProcessor{process(inputs){const ch=inputs[0][0];if(ch){const i16=new Int16Array(ch.length);for(let i=0;i<ch.length;i++)i16[i]=Math.max(-32768,Math.min(32767,ch[i]*32768));this.port.postMessage(i16.buffer,[i16.buffer]);}return true;}}registerProcessor('pcm-processor',PCMProcessor);"],{type:'application/javascript'})));
            audioWorkletNode = new AudioWorkletNode(audioContext,'pcm-processor');
            src.connect(audioWorkletNode);
            audioWorkletNode.port.onmessage = e => {
                if (ws && ws.readyState===WebSocket.OPEN)
                    ws.send(JSON.stringify({realtimeInput:{mediaChunks:[{mimeType:'audio/pcm',data:ab2b64(e.data)}]}}));
            };
            UI.chatInput.removeAttribute('disabled'); UI.sendTextBtn.removeAttribute('disabled');
            UI.chatInput.placeholder = 'Type a message...';
            startSR();
            addMsg('Voice agent connected!', 'system');
        };
        ws.onmessage = async e => {
            const msg = JSON.parse(e.data);
            if (msg.toolCall) {
                const call = msg.toolCall.functionCalls[0];
                addTool(call.name+'()\n'+JSON.stringify(call.args,null,2));
                try {
                    const r = await fetch('http://127.0.0.1:5000/api/tool_call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({tool_name:call.name,tool_args:call.args,user_id:currentUser.id})});
                    const result = await r.json();
                    ws.send(JSON.stringify({toolResponse:{functionResponses:[{id:call.id,name:call.name,response: typeof result === 'object' && result !== null ? result : { output: result }}]}}));
                } catch(err) {
                    ws.send(JSON.stringify({toolResponse:{functionResponses:[{id:call.id,name:call.name,response:{ error: err.message }}]}}));
                }
            }
            if (msg.serverContent) {
                const c = msg.serverContent;
                if (c.inputTranscription&&c.inputTranscription.text) addMsg(c.inputTranscription.text,'user',true);
                if (c.outputTranscription&&c.outputTranscription.text) { updateStatus('Agent Speaking...','speaking'); addMsg(c.outputTranscription.text,'ai',true); }
                if (c.modelTurn) { for (const p of c.modelTurn.parts) { if (p.inlineData) playB64(p.inlineData.data); } }
                if (c.turnComplete) { updateStatus('Listening...','live'); activeBubble=null; }
            }
        };
        ws.onclose = () => { 
            if (pingTimer) clearInterval(pingTimer);
            let wasActive = isCallActive && !isCleaningUp;
            isCallActive = false; 
            cleanUp(); 
            if (wasActive) {
                addMsg('Connection lost. Reconnecting in 3 seconds...', 'system');
                setTimeout(() => { if (!isCallActive && typeof isCleaningUp !== "undefined" && !isCleaningUp) UI.callBtn.click(); else if (!isCallActive) UI.callBtn.click(); }, 3000);
            }
        };
    } else { stopCall(); }
});

function stopCall() { if (ws) ws.close(); cleanUp(); }

function cleanUp() {
    UI.callBtn.classList.remove('active');
    UI.callBtnText.textContent = 'Start Session';
    updateStatus('Call Ended','muted');
    flushBufs();
    setTimeout(summarize, 1500);
    UI.chatInput.setAttribute('disabled','true'); UI.sendTextBtn.setAttribute('disabled','true');
    UI.chatInput.placeholder = 'Connect a call to type...'; UI.chatInput.value = '';
    stopSR();
    if (audioWorkletNode) audioWorkletNode.disconnect();
    if (mediaStream) mediaStream.getTracks().forEach(t=>t.stop());
    if (audioContext) audioContext.close();
    if (ws) { ws.close(); ws=null; }
}

async function summarize() {
    if (!sessionId||!currentUser) return;
    addMsg('Saving summary...','system');
    try {
        const r = await fetch('http://127.0.0.1:5000/api/summarize_and_email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session_id:sessionId,user_id:currentUser.id})});
        const d = await r.json(); addMsg(d.result,'system'); fetchHistory();
    } catch(e) { addMsg('Summary failed.','system'); }
}

function ab2b64(buf) { let b='',u=new Uint8Array(buf); for(let i=0;i<u.byteLength;i++) b+=String.fromCharCode(u[i]); return window.btoa(b); }

function playB64(b64) {
    if (!audioContext) return;
    const bin=atob(b64),buf=new ArrayBuffer(bin.length),view=new DataView(buf);
    for(let i=0;i<bin.length;i++) view.setUint8(i,bin.charCodeAt(i));
    const i16=new Int16Array(buf),ab=audioContext.createBuffer(1,i16.length,24000);
    const ch=ab.getChannelData(0); for(let i=0;i<i16.length;i++) ch[i]=i16[i]/32768;
    const src=audioContext.createBufferSource(); src.buffer=ab;
    src.connect(aiAnalyser); aiAnalyser.connect(audioContext.destination);
    const st=Math.max(audioContext.currentTime,nextPlayTime); src.start(st); nextPlayTime=st+ab.duration;
    activeSources.push(src); src.onended=()=>{ activeSources=activeSources.filter(s=>s!==src); };
}

UI.sendTextBtn.addEventListener('click', () => {
    const t = UI.chatInput.value.trim();
    if (!t||!ws||ws.readyState!==WebSocket.OPEN) return;
    ws.send(JSON.stringify({clientContent:{turns:[{role:'user',parts:[{text:t}]}],turnComplete:true}}));
    addMsg(t,'user',false); UI.chatInput.value='';
});
UI.chatInput.addEventListener('keypress', e => { if(e.key==='Enter') UI.sendTextBtn.click(); });

window.addEventListener('online', () => { UI.networkAlert.classList.add('hidden'); if(isCallActive) updateStatus('Listening...','live'); });
window.addEventListener('offline', () => { UI.networkAlert.classList.remove('hidden'); updateStatus('Offline',''); });
UI.triggerCellularBtn.addEventListener('click', async () => {
    if (!currentUser) return;
    try { const r=await fetch('http://127.0.0.1:5000/api/trigger_phone_call',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({user_id:currentUser.id,text_to_say:'Browser disconnected. Switching to cellular.'})}); const d=await r.json(); alert(d.result); UI.networkAlert.classList.add('hidden'); }
    catch(err) { alert('Failed: '+err); }
});

// ORB RENDERER
function renderOrb() {
    requestAnimationFrame(renderOrb);
    const canvas=UI.orbCanvas, ctx=canvas.getContext('2d');
    const W=canvas.width, H=canvas.height, cx=W/2, cy=H/2;
    ctx.clearRect(0,0,W,H);
    let mv=0, av=0;
    if (isCallActive && micAnalyser && aiAnalyser) {
        const md=new Uint8Array(micAnalyser.frequencyBinCount); micAnalyser.getByteTimeDomainData(md);
        let ms=0; for(let i=0;i<md.length;i++) ms+=Math.abs(md[i]-128); mv=ms/md.length;
        const ad=new Uint8Array(aiAnalyser.frequencyBinCount); aiAnalyser.getByteTimeDomainData(ad);
        let as_=0; for(let i=0;i<ad.length;i++) as_+=Math.abs(ad[i]-128); av=as_/ad.length;
    }
    phase += isCallActive ? (0.05+(mv+av)*0.005) : 0.018;
    const baseR = isCallActive ? (72+mv*0.6+av*1.1) : (64+Math.sin(Date.now()/900)*4);
    const bg = ctx.createRadialGradient(cx,cy,0,cx,cy,baseR*1.8);
    const ga = isCallActive ? (0.08+(mv+av)/120) : 0.04;
    bg.addColorStop(0,'rgba(124,109,250,'+ga+')'); bg.addColorStop(0.6,'rgba(124,109,250,0.01)'); bg.addColorStop(1,'rgba(0,0,0,0)');
    ctx.fillStyle=bg; ctx.fillRect(0,0,W,H);
    const layers = isCallActive ? [
        {r:baseR,       amp:13+mv*0.5+av*0.9, freq:4, ph:phase,        c:'rgba(124,109,250,0.9)', lw:2.5, bl:14},
        {r:baseR*0.9,   amp:10+mv*0.4+av*0.7, freq:5, ph:-phase*1.1,   c:'rgba(167,139,250,0.7)', lw:1.8, bl:9},
        {r:baseR*1.08,  amp:7+mv*0.3+av*0.55, freq:3, ph:phase*0.8,    c:'rgba(99,102,241,0.5)',  lw:1.2, bl:6},
        {r:baseR*1.16,  amp:4+av*0.3,          freq:6, ph:-phase*0.6,   c:'rgba(124,109,250,0.2)', lw:0.8, bl:3},
    ] : [
        {r:baseR,       amp:3,   freq:2, ph:phase,       c:'rgba(124,109,250,0.35)', lw:1.5, bl:8},
        {r:baseR*0.92,  amp:2.2, freq:3, ph:-phase*0.9,  c:'rgba(167,139,250,0.2)',  lw:1,   bl:5},
        {r:baseR*1.08,  amp:1.8, freq:2, ph:phase*0.7,   c:'rgba(99,102,241,0.15)', lw:0.8, bl:3},
    ];
    layers.forEach(l => {
        ctx.beginPath(); ctx.lineWidth=l.lw; ctx.strokeStyle=l.c;
        ctx.shadowBlur=l.bl; ctx.shadowColor='rgba(124,109,250,0.5)';
        const pts=100;
        for(let j=0;j<=pts;j++) {
            const a=(j/pts)*Math.PI*2, off=Math.sin(a*l.freq+l.ph)*l.amp, r=l.r+off;
            const x=cx+Math.cos(a)*r, y=cy+Math.sin(a)*r;
            j===0 ? ctx.moveTo(x,y) : ctx.lineTo(x,y);
        }
        ctx.closePath(); ctx.stroke();
    });
    ctx.shadowBlur=0; ctx.shadowColor='transparent';
    UI.orbGlow.style.opacity = isCallActive ? String(Math.min(1,0.5+(mv+av)/60)) : '0.35';
}

// DRAWER + PROFILE WIRING
document.getElementById('drawerHandle').addEventListener('click', () => UI.chatDrawer.classList.toggle('open'));
document.getElementById('closeDrawerBtn').addEventListener('click', () => UI.chatDrawer.classList.remove('open'));
document.getElementById('openTranscriptBtn').addEventListener('click', () => UI.chatDrawer.classList.add('open'));
document.getElementById('openDrawerBtn').addEventListener('click', () => document.getElementById('historyDrawer').classList.add('open'));
document.getElementById('closeHistoryBtn').addEventListener('click', () => document.getElementById('historyDrawer').classList.remove('open'));
document.getElementById('profileTrigger').addEventListener('click', e => { e.stopPropagation(); document.getElementById('profileMenu').classList.toggle('open'); });
document.addEventListener('click', e => { if(!document.getElementById('profileMenu').contains(e.target)) document.getElementById('profileMenu').classList.remove('open'); });
document.getElementById('googleAuthBtn').addEventListener('click', () => { if(currentUser) window.location.href='http://127.0.0.1:5000/auth/login?user_id='+currentUser.id; });

window.addEventListener('load', () => {
    const su=localStorage.getItem('user'), sk=localStorage.getItem('gemini_api_key');
    if (su && sk) { currentUser=JSON.parse(su); UI.geminiKey.value=sk; UI.authModal.classList.add('hidden'); loadUserProfile(); }
    enumerateMics();
    const p = new URLSearchParams(window.location.search);
    if (p.has('auth_success')) { addMsg('Google Calendar connected!','system'); window.history.replaceState({},document.title,window.location.pathname); }
    renderOrb();
    if (typeof gsap !== 'undefined') {
        gsap.from('.nav', {y:-18, opacity:0, duration:0.7, ease:'power3.out'});
        gsap.from('.stage > *', {y:20, opacity:0, duration:0.7, stagger:0.1, ease:'power3.out', delay:0.15});
    }
});
</script>
</body>
</html>"""

with open(r'index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f'Written {len(html)} bytes, {html.count(chr(10))} lines')
