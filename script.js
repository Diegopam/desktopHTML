document.addEventListener('DOMContentLoaded', () => {
    /* ---------- Estado base ---------- */
    let contador = 0;
    let globalZ = 1;
    const centerArea = document.getElementById("centerArea");
    const startBtn = document.getElementById("startBtn");
    const startMenu = document.getElementById("startMenu");
    const backdrop = document.getElementById("backdrop");
    const searchInput = document.getElementById("menuSearch");

    /* ---------- Classe de Janela (seu código com min ajustes) ---------- */
    class Janela {
        constructor(titulo, conteudoHTML) {
            this.id = "janela_" + (++contador);
            this.titulo = titulo;
            this.minimizado = false;

            this.win = document.createElement("div");
            this.win.className = "window";
            this.win.style.top = `${50 + contador * 20}px`;
            this.win.style.left = `${50 + contador * 20}px`;
            this.win.style.zIndex = globalZ++;

            this.win.innerHTML = `
      <div class="titlebar">
        <span>${titulo}</span>
        <div class="buttons">
          <div class="btn minimize" title="Minimizar"></div>
          <div class="btn maximize" title="Maximizar/Restaurar"></div>
          <div class="btn close" title="Fechar"></div>
        </div>
      </div>
      <div class="content">${conteudoHTML || "Conteúdo da " + titulo}</div>
      <div class="resizer nw"></div>
      <div class="resizer ne"></div>
      <div class="resizer sw"></div>
      <div class="resizer se"></div>
      <div class="resizer n"></div>
      <div class="resizer s"></div>
      <div class="resizer e"></div>
      <div class="resizer w"></div>
    `;
            document.getElementById("desktop").appendChild(this.win);

            this.taskBtn = document.createElement("button");
            this.taskBtn.className = "task-btn task-item";
            this.taskBtn.textContent = titulo;
            centerArea.appendChild(this.taskBtn);

            this.#ativarEventos();
        }

        #ativarEventos() {
            const bar = this.win.querySelector(".titlebar");
            const [minBtn, maxBtn, closeBtn] = this.win.querySelectorAll(".btn");
            const resizers = this.win.querySelectorAll(".resizer");
            let ativo = false, offsetX, offsetY;

            const startDrag = (e) => {
                this.win.style.zIndex = ++globalZ;
                if (this.win.dataset.max) { this.#restoreDefaultSize(); }
                ativo = true;
                const p = e.touches ? e.touches[0] : e;
                offsetX = p.clientX - this.win.offsetLeft;
                offsetY = p.clientY - this.win.offsetTop;
            };
            const onDrag = (e) => {
                if (!ativo) return;
                const p = e.touches ? e.touches[0] : e;
                this.win.style.left = (p.clientX - offsetX) + "px";
                this.win.style.top = (p.clientY - offsetY) + "px";
            };
            const stopDrag = () => { ativo = false; };

            bar.addEventListener("mousedown", startDrag);
            bar.addEventListener("touchstart", startDrag, { passive: true });
            document.addEventListener("mousemove", onDrag);
            document.addEventListener("touchmove", onDrag, { passive: false });
            document.addEventListener("mouseup", stopDrag);
            document.addEventListener("touchend", stopDrag);

            // Redimensionamento
            let resizing = false, currentResizer = null, initX, initY, initW, initH, initTop, initLeft;
            const startResize = (e) => {
                currentResizer = e.target; resizing = true; this.win.style.zIndex = ++globalZ;
                const p = e.touches ? e.touches[0] : e;
                initX = p.clientX; initY = p.clientY;
                initW = this.win.offsetWidth; initH = this.win.offsetHeight;
                initTop = this.win.offsetTop; initLeft = this.win.offsetLeft;
                e.preventDefault();
            };
            const onResize = (e) => {
                if (!resizing) return;
                const p = e.touches ? e.touches[0] : e;
                const x = p.clientX, y = p.clientY;
                const minW = 150, minH = 100;

                if (currentResizer.classList.contains("se")) {
                    this.win.style.width = Math.max(minW, initW + (x - initX)) + "px";
                    this.win.style.height = Math.max(minH, initH + (y - initY)) + "px";
                } else if (currentResizer.classList.contains("sw")) {
                    let newW = Math.max(minW, initW - (x - initX));
                    this.win.style.width = newW + "px";
                    this.win.style.left = initLeft + (initW - newW) + "px";
                    this.win.style.height = Math.max(minH, initH + (y - initY)) + "px";
                } else if (currentResizer.classList.contains("ne")) {
                    this.win.style.width = Math.max(minW, initW + (x - initX)) + "px";
                    let newH = Math.max(minH, initH - (y - initY));
                    this.win.style.height = newH + "px";
                    this.win.style.top = initTop + (initH - newH) + "px";
                } else if (currentResizer.classList.contains("nw")) {
                    let newW = Math.max(minW, initW - (x - initX));
                    let newH = Math.max(minH, initH - (y - initY));
                    this.win.style.width = newW + "px"; this.win.style.height = newH + "px";
                    this.win.style.top = initTop + (initH - newH) + "px";
                    this.win.style.left = initLeft + (initW - newW) + "px";
                } else if (currentResizer.classList.contains("n")) {
                    let newH = Math.max(minH, initH - (y - initY));
                    this.win.style.height = newH + "px";
                    this.win.style.top = initTop + (initH - newH) + "px";
                } else if (currentResizer.classList.contains("s")) {
                    this.win.style.height = Math.max(minH, initH + (y - initY)) + "px";
                } else if (currentResizer.classList.contains("e")) {
                    this.win.style.width = Math.max(minW, initW + (x - initX)) + "px";
                } else if (currentResizer.classList.contains("w")) {
                    let newW = Math.max(minW, initW - (x - initX));
                    this.win.style.width = newW + "px";
                    this.win.style.left = initLeft + (initW - newW) + "px";
                }
            };
            const stopResize = () => { resizing = false; currentResizer = null; };

            resizers.forEach(r => {
                r.addEventListener("mousedown", startResize);
                r.addEventListener("touchstart", startResize, { passive: false });
            });
            document.addEventListener("mousemove", onResize);
            document.addEventListener("touchmove", onResize, { passive: false });
            document.addEventListener("mouseup", stopResize);
            document.addEventListener("touchend", stopResize);

            // Botões de janela
            this.taskBtn.onclick = () => this.toggleMin();
            minBtn.onclick = () => this.toggleMin();
            closeBtn.onclick = () => { this.win.remove(); this.taskBtn.remove(); };
            maxBtn.onclick = () => this.toggleMax();

            // Foco ao clicar
            this.win.addEventListener("mousedown", () => this.win.style.zIndex = ++globalZ);
        }

        #restoreDefaultSize() {
            this.win.style.width = "300px";
            this.win.style.height = "200px";
            this.win.dataset.max = "";
        }

        toggleMin() {
            this.minimizado = !this.minimizado;
            this.win.style.display = this.minimizado ? "none" : "flex";
            if (!this.minimizado) this.win.style.zIndex = ++globalZ;
        }
        toggleMax() {
            this.win.style.zIndex = ++globalZ;
            if (this.win.dataset.max) {
                this.#restoreDefaultSize();
                this.win.style.top = `50px`; this.win.style.left = `50px`;
                delete this.win.dataset.max;
            } else {
                this.win.style.top = "0"; this.win.style.left = "0";
                this.win.style.width = "100%"; this.win.style.height = "calc(100vh - 40px)";
                this.win.dataset.max = true;
            }
        }
    }

    /* ---------- Apps do Menu ---------- */
    const apps = [
        {
            icon: "📝", label: "Notas", open: () => novaJanela("Notas",
                `<h3>Notas</h3><p>Bem-vinde às suas notas.</p><textarea style="width:100%;height:120px"></textarea>`)
        },
        {
            icon: "🌐", label: "Navegador", open: () => novaJanela("Navegador",
                `<div style="display:flex;gap:6px;margin-bottom:6px">
       <input id='url' placeholder='https://…' style="flex:1;padding:6px"/>
       <button onclick="const f=this.parentElement.nextElementSibling;f.src=this.previousElementSibling.value||'https://duckduckgo.com'">Ir</button>
     </div>
     <iframe src="https://duckduckgo.com" style="width:100%;height:70vh;border:0"></iframe>` )
        },
        {
            icon: "💻", label: "Terminal", open: () => novaJanela("Terminal",
                `<pre style="background:#111;color:#0f0;padding:10px;border-radius:8px;min-height:140px;overflow:auto">simulando $ echo "hello world"</pre>`)
        },
        {
            icon: "🖼️", label: "Galeria", open: () => novaJanela("Galeria",
                `<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:6px">
      ${Array.from({ length: 6 }).map((_, i) => `<div style="aspect-ratio:1/1;background:#ddd;border-radius:8px;display:flex;align-items:center;justify-content:center">IMG ${i + 1}</div>`).join("")}
     </div>` )
        },
        {
            icon: "⚙️", label: "Configurações", open: () => novaJanela("Configurações",
                `<label style="display:flex;align-items:center;gap:8px"><input type="checkbox"/> Ativar modo turbo da Verônica</label>
     <p class="muted">Sem garantias contratuais, só estilo.</p>` )
        },
        {
            icon: "🗂️", label: "Arquivos", open: () => novaJanela("Arquivos",
                `<ul><li>/home/diego/projetos</li><li>/home/diego/roms</li><li>/home/diego/downloads</li></ul>`)
        },
    ];

    /* ---------- Quick actions ---------- */
    const quickActions = [
        { label: "Nova janela vazia", action: () => novaJanela("Janela") },
        { label: "Abrir três janelas", action: () => { novaJanela("Notas"); novaJanela("Navegador"); novaJanela("Terminal"); } },
        { label: "Organizar lado a lado", action: tileWindowsSideBySide },
    ];

    /* ---------- Render do menu ---------- */
    function renderMenu() {
        const grid = document.getElementById("appsGrid");
        grid.innerHTML = "";
        apps.forEach(app => {
            const el = document.createElement("div");
            el.className = "app";
            el.innerHTML = `<div class="icon">${app.icon}</div><div class="label">${app.label}</div>`;
            el.onclick = () => { app.open(); closeMenu(); };
            grid.appendChild(el);
        });

        const ql = document.getElementById("quickList");
        ql.innerHTML = "";
        quickActions.forEach(q => {
            const el = document.createElement("div");
            el.className = "quick-item";
            el.textContent = q.label;
            el.onclick = () => { closeMenu(); q.action(); };
            ql.appendChild(el);
        });
    }

    /* ---------- Menu: abrir/fechar/pesquisa ---------- */
    function openMenu() {
        startMenu.classList.add("show");
        backdrop.classList.add("show");
        startMenu.setAttribute("aria-hidden", "false");
        searchInput.value = "";
        searchInput.focus();
    }
    function closeMenu() {
        startMenu.classList.remove("show");
        backdrop.classList.remove("show");
        startMenu.setAttribute("aria-hidden", "true");
    }
    function toggleMenu() { startMenu.classList.contains("show") ? closeMenu() : openMenu(); }

    startBtn.addEventListener("click", toggleMenu);
    backdrop.addEventListener("click", closeMenu);

    searchInput.addEventListener("input", (e) => {
        const term = e.target.value.toLowerCase();
        const nodes = [...document.querySelectorAll("#appsGrid .app")];
        nodes.forEach(n => {
            const label = n.querySelector(".label").textContent.toLowerCase();
            n.style.display = label.includes(term) ? "" : "none";
        });
    });
    // Pressionar "/" foca a busca
    document.addEventListener("keydown", (e) => {
        if (e.key === "Meta") { toggleMenu(); }
        if (e.key === "Escape") { closeMenu(); }
        if (e.key === "/") { if (!startMenu.classList.contains("show")) openMenu(); e.preventDefault(); searchInput.focus(); }
    });

    /* ---------- Utilidades ---------- */
    function novaJanela(titulo, conteudo) { new Janela(titulo, conteudo); }

    function tileWindowsSideBySide() {
        const windows = [...document.querySelectorAll(".window")];
        if (windows.length < 2) return;
        const availW = window.innerWidth, availH = window.innerHeight - 40; // - taskbar
        const cols = Math.ceil(Math.sqrt(windows.length));
        const rows = Math.ceil(windows.length / cols);
        const cellW = Math.floor(availW / cols), cellH = Math.floor(availH / rows);
        windows.forEach((w, i) => {
            const r = Math.floor(i / cols), c = i % cols;
            w.style.top = (r * cellH) + "px";
            w.style.left = (c * cellW) + "px";
            w.style.width = (cellW) + "px";
            w.style.height = (cellH) + "px";
            w.dataset.max = ""; // garantir não-maximizada
            w.style.display = "flex";
        });
    }

    /* ---------- Clock ---------- */
    function updateClock() {
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, "0");
        const mm = String(now.getMinutes()).padStart(2, "0");
        document.getElementById("clock").textContent = `${hh}:${mm}`;
    }
    setInterval(updateClock, 1000); updateClock();

    /* ---------- Inicialização ---------- */
    renderMenu();
    // Abra algumas janelas de demonstração
    novaJanela("Notas");
    novaJanela("Navegador");
    novaJanela("Terminal");

    // Power (demonstração)
    document.getElementById("btnLock").onclick = () => { closeMenu(); alert("Bloquear: placeholder"); };
    document.getElementById("btnLogout").onclick = () => { closeMenu(); alert("Sair: placeholder"); };
    document.getElementById("btnShutdown").onclick = () => { closeMenu(); alert("Desligar: placeholder"); };
});