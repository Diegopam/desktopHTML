#!/usr/bin/env python3
import os
# FORÇAR AMBIENTE KDE: Esta linha é uma tentativa de resolver o erro 'Invalid session'
# ao dar uma dica explícita ao sistema de portais sobre qual backend usar.
# Deve ser uma das primeiras linhas a serem executadas.
os.environ['XDG_CURRENT_DESKTOP'] = 'KDE'
import sys
import json
import importlib.util
import subprocess
from pathlib import Path
import handler
from concurrent.futures import ThreadPoolExecutor

# Adiciona a importação do WeasyPrint e uma verificação
try:
    from weasyprint import HTML
    WEASYPRINT_OK = True
except ImportError:
    WEASYPRINT_OK = False
    print("[AVISO] Biblioteca 'weasyprint' não encontrada. A exportação para PDF não funcionará.")

def log(msg):
    print(f"[RaijinForge] {msg}")

def detectar_distro():
    try:
        with open("/etc/os-release") as f:
            for linha in f:
                if linha.startswith("ID="):
                    return linha.strip().split("=")[1].replace('"', '')
    except:
        return "desconhecido"

def verificar_tk_instalado_ou_instalar():
    try:
        import tkinter
        return True
    except ImportError:
        log("Tkinter ausente. Tentando instalar automaticamente...")
        distro = detectar_distro()

        if distro in ["arch", "manjaro"]:
            comando = "pkexec pacman -Sy --noconfirm tk"
        elif distro in ["ubuntu", "debian", "linuxmint"]:
            comando = "pkexec apt update && pkexec apt install -y python3-tk"
        elif distro in ["fedora"]:
            comando = "pkexec dnf install -y python3-tkinter"
        else:
            log("Distro desconhecida. Instalação automática do Tkinter não suportada.")
            return False

        try:
            subprocess.run(["bash", "-c", comando])
            log("Tkinter instalado com sucesso. Reiniciando o app...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            log(f"Erro ao tentar instalar o Tkinter: {e}")
            return False

def verificar_e_instalar_dependencias_pip():
    """Lê requirements.txt, verifica as dependências e as instala se necessário."""
    base_dir = Path(__file__).resolve().parent
    requirements_file = base_dir / "requirements.txt"

    if not requirements_file.is_file():
        log("Arquivo requirements.txt não encontrado. Pulando verificação de dependências pip.")
        return True # Assume que está tudo bem se o arquivo não existe

    with open(requirements_file, "r") as f:
        # Lê as dependências, ignorando comentários e linhas vazias
        # Também lida com especificadores de versão (ex: psutil==5.9.0) pegando só o nome do módulo
        pacotes_necessarios = [
            line.strip().split("==")[0].split(">=")[0].split("<=")[0].split("!=")[0]
            for line in f if line.strip() and not line.strip().startswith("#")
        ]

    pacotes_faltando = []
    for pacote in pacotes_necessarios:
        # Tenta importar o módulo. É mais robusto que find_spec, pois detecta
        # instalações quebradas que causam ImportError.
        try:
            importlib.import_module(pacote)
        except ImportError:
            log(f"Dependência pip '{pacote}' não encontrada ou com erro na importação.")
            pacotes_faltando.append(pacote)

    if not pacotes_faltando:
        log("Todas as dependências pip estão satisfeitas.")
        return True

    log(f"Dependências pip faltando: {', '.join(pacotes_faltando)}")

    # Usa o tkinter que já foi verificado para pedir permissão
    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.withdraw() # Não precisamos da janela principal do tkinter

    resposta = messagebox.askyesno(
        "Dependências Ausentes",
        "Algumas bibliotecas Python necessárias para o aplicativo não estão instaladas:\n\n"
        f" - {', '.join(pacotes_faltando)}\n\n"
        "Deseja que o sistema tente instalá-las automaticamente usando 'pip'?"
    )

    if resposta:
        # Adiciona --user para instalar no diretório do usuário, evitando problemas de permissão.
        # Adiciona --no-cache-dir para forçar o download e evitar problemas com cache corrompido.
        # Adiciona --break-system-packages para contornar proteções de pacotes do sistema (PEP 668).
        log(f"Usuário autorizou. Instalando via: pip install --user --no-cache-dir --break-system-packages -r {requirements_file}")
        comando = [sys.executable, "-m", "pip", "install", "--user", "--no-cache-dir", "--break-system-packages", "-r", str(requirements_file)]
        try:
            subprocess.run(comando, check=True, capture_output=True, text=True)
            messagebox.showinfo("Sucesso", "Dependências instaladas com sucesso!\nO aplicativo será reiniciado.")
            root.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            erro_msg = f"Falha ao instalar dependências com pip.\n\nErro: {getattr(e, 'stderr', e)}\n\nPor favor, instale manualmente: pip install -r {requirements_file}"
            messagebox.showerror("Erro de Instalação", erro_msg)
            return False
    else:
        return False

def detectar_ambiente():
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    session = os.environ.get("DESKTOP_SESSION", "").lower()
    log(f"Detectando ambiente... Desktop: {desktop}, Sessão: {session}")
    if "gnome" in desktop or "xfce" in desktop or "cinnamon" in desktop:
        return "gtk"
    elif "kde" in desktop or "plasma" in desktop or "lxqt" in desktop or "qt" in session:
        return "qt"
    return "desconhecido"

def dependencias_ok(ambiente):
    try:
        import gi
        for tentativa in ["4.0", "4.1", "5.0"]:
            try:
                gi.require_version('WebKit2', tentativa)
                from gi.repository import WebKit2
                log(f"WebKit2GTK detectado: versão {tentativa}")
                return tentativa
            except (ValueError, ImportError):
                continue
        return None
    except ImportError as e:
        log(f"[ERRO] GTK não disponível: {e}")
        return None

def chamar_instalador_embutido():
    import tkinter as tk
    from tkinter import messagebox

    def detectar_webkit_disponivel():
        distro = detectar_distro()
        if distro in ["ubuntu", "debian", "linuxmint"]:
            try:
                result = subprocess.run(["apt-cache", "search", "gir1.2-webkit2"], capture_output=True, text=True)
                linhas = result.stdout.splitlines()
                versoes = [
                    linha.split(" ", 1)[0].replace("gir1.2-webkit2-", "")
                    for linha in linhas if linha.startswith("gir1.2-webkit2-")
                ]
                return sorted(versoes, reverse=True)[0] if versoes else None
            except Exception as e:
                print(f"[!] Erro ao detectar WebKit disponível: {e}")
                return None
        else:
            return "4.0"

    def instalar():
        distro = detectar_distro()
        versao_disponivel = detectar_webkit_disponivel()
        if not versao_disponivel:
            messagebox.showerror("Erro", "Nenhuma versão do WebKit2GTK foi encontrada.")
            return

        if distro in ["ubuntu", "debian", "linuxmint"]:
            comando = (
                f"sudo add-apt-repository universe && sudo apt update && "
                f"sudo apt install -y python3-gi gir1.2-webkit2-{versao_disponivel} jq curl playerctl"
            )
        elif distro in ["arch", "manjaro"]:
            comando = "sudo pacman -Syu --noconfirm python-gobject webkit2gtk jq curl playerctl"
        elif distro in ["fedora"]:
            comando = "sudo dnf install -y python3-gobject webkit2gtk3 jq curl playerctl"
        else:
            messagebox.showerror("Erro", f"Distro não suportada: {distro}")
            return

        try:
            subprocess.run(["pkexec", "bash", "-c", comando])
            messagebox.showinfo("Sucesso", "Dependências instaladas! O app será reiniciado.")
            root.destroy()
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao instalar: {e}")

    root = tk.Tk()
    root.title("Instalador de Dependências")
    root.geometry("500x200")
    label = tk.Label(root, text="Dependências ausentes.\nClique no botão para instalar.", font=("Arial", 12))
    label.pack(pady=20)
    botao = tk.Button(root, text="Instalar Dependências", command=instalar, font=("Arial", 12), bg="#4CAF50", fg="white")
    botao.pack(pady=10)
    root.mainloop()

def iniciar_gtk(versao_webkit):
    import gi
    gi.require_version('Gtk', '3.0')
    gi.require_version('WebKit2', versao_webkit)
    from gi.repository import Gtk, WebKit2, GLib, Gdk


    class NavegadorWindow(Gtk.Window):
        """ Uma classe para a janela nativa do navegador com topbar fixa. """
        def __init__(self, main_app, win_id, url, tema, manager):
            super().__init__(title="Navegador")
            self.main_app = main_app
            self.win_id = win_id
            self.favorites = []
            self.topbar_collapsed = False
            # NOVO: Gerenciamento de abas
            self.tabs = []
            self.active_tab_id = None
            self.next_tab_numeric_id = 0
            self.tema = tema

            self.set_default_size(1024, 768)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_decorated(False) # Remove a barra de título padrão

            # Container principal
            self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

            # NOVO: Overlay para diálogos
            self.overlay = Gtk.Overlay()
            self.overlay.add(self.box) # Adiciona o conteúdo principal ao overlay
            self.add(self.overlay) # Adiciona o overlay à janela

            # NOVO: Placeholder para a view do diálogo
            self.dialog_view = None
            # WebView para a Topbar
            self.topbar_view = WebKit2.WebView.new_with_user_content_manager(manager)
            # A altura é controlada pelo CSS injetado em topbar.js, mas podemos dar um request inicial
            self.topbar_view.set_size_request(-1, 95) # Altura para topbar + favoritos
            self.topbar_view.connect("load-changed", self.on_topbar_load_changed)
            
            # NOVO: Gtk.Stack para gerenciar as WebViews de conteúdo (abas)
            self.content_stack = Gtk.Stack()
            self.content_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            self.content_stack.set_transition_duration(200)

            # Adiciona as WebViews ao box
            self.box.pack_start(self.topbar_view, False, False, 0)
            self.box.pack_start(self.content_stack, True, True, 0)

            # Carrega os conteúdos
            topbar_path = self.main_app.base_dir / "topbar.html"
            self.topbar_view.load_uri(f"file://{topbar_path}")
            self._criar_nova_aba(url) # Cria a primeira aba

            # Sinais da janela
            self.connect("destroy", self.on_destroy_event)
            self.connect("window-state-event", self.on_window_state_change)
            
            # Aplica o tema
            settings = Gtk.Settings.get_default()
            # CORREÇÃO: Determina se o tema é escuro pela terminação '-dark' ou '-light'
            is_dark_theme = not tema.endswith('-light')
            settings.set_property("gtk-application-prefer-dark-theme", is_dark_theme)

            self.show_all()

        def show_favorite_dialog(self, url, default_name):
            """Cria e exibe uma WebView de diálogo sobre o conteúdo principal."""
            if self.dialog_view:
                log("Um diálogo já está aberto nesta janela.")
                return

            # Cria uma nova WebView para o diálogo
            dialog_manager = WebKit2.UserContentManager()
            # Usa uma ponte de mensagem diferente para não conflitar com a principal
            dialog_manager.register_script_message_handler("dialog_bridge")
            dialog_manager.connect("script-message-received::dialog_bridge", self.on_dialog_message)
            
            self.dialog_view = WebKit2.WebView.new_with_user_content_manager(dialog_manager)
            self.dialog_view.set_background_color(Gdk.RGBA(0, 0, 0, 0.5)) # Fundo semi-transparente
            
            # Carrega o HTML do diálogo
            dialog_path = self.main_app.base_dir / "browser_dialog.html"
            self.dialog_view.load_uri(f"file://{dialog_path}")

            # Injeta os dados no diálogo assim que ele carregar
            def on_dialog_load(webview, load_event):
                if load_event == WebKit2.LoadEvent.FINISHED:
                    init_data = {"url": url, "defaultName": default_name}
                    js_code = f"window.initializeDialog({json.dumps(init_data)})"
                    webview.run_javascript(js_code, None, None, None)

            self.dialog_view.connect("load-changed", on_dialog_load)

            # Adiciona a view do diálogo ao overlay e a exibe
            self.overlay.add_overlay(self.dialog_view)
            self.dialog_view.show()

        def hide_favorite_dialog(self):
            """Remove e destrói a WebView do diálogo."""
            if self.dialog_view:
                self.overlay.remove(self.dialog_view)
                # Desconectar sinais aqui se necessário para evitar memory leaks
                self.dialog_view = None
                log("Diálogo do navegador fechado.")

        def _get_tab_by_id(self, tab_id):
            return next((tab for tab in self.tabs if tab['id'] == tab_id), None)

        def _get_tab_by_view(self, view):
            return next((tab for tab in self.tabs if tab['view'] == view), None)

        def _notificar_js_sobre_abas(self):
            """Envia a lista atual de abas para a topbar renderizar."""
            tabs_data = [
                {"id": tab["id"], "title": tab["title"], "isActive": tab["id"] == self.active_tab_id}
                for tab in self.tabs
            ]
            js_code = f"window.updateTabs({json.dumps(tabs_data)})"
            self.topbar_view.run_javascript(js_code, None, None, None)

        def _criar_nova_aba(self, url="https://google.com"):
            """Cria uma nova WebView, adiciona ao Stack e atualiza o estado."""
            tab_id = f"tab_{self.next_tab_numeric_id}"
            self.next_tab_numeric_id += 1

            new_view = WebKit2.WebView.new_with_user_content_manager(self.main_app.manager)
            
            new_tab = {"id": tab_id, "view": new_view, "title": "Nova Aba"}
            self.tabs.append(new_tab)

            # Conecta os sinais para esta aba específica
            new_view.connect("load-changed", self.on_content_load_changed, new_tab)
            new_view.connect("notify::title", self.on_content_title_changed, new_tab)
            new_view.connect("enter-fullscreen", self.on_enter_fullscreen)
            new_view.connect("leave-fullscreen", self.on_leave_fullscreen)

            self.content_stack.add_named(new_view, tab_id)
            new_view.show()
            new_view.load_uri(url)
            
            self._trocar_para_aba(tab_id)

        def _trocar_para_aba(self, tab_id):
            tab = self._get_tab_by_id(tab_id)
            if not tab: return

            self.content_stack.set_visible_child_name(tab_id)
            self.active_tab_id = tab_id
            self._notificar_js_sobre_abas()
            self.on_content_title_changed(tab['view'], None, tab) # Força a atualização do título da janela

        def _fechar_aba(self, tab_id):
            tab_a_fechar = self._get_tab_by_id(tab_id)
            if not tab_a_fechar: return

            # Se for a última aba, fecha a janela inteira
            if len(self.tabs) <= 1:
                self.close()
                return

            # Remove a aba e sua view
            self.content_stack.remove(tab_a_fechar['view'])
            self.tabs.remove(tab_a_fechar)

            # Se a aba fechada era a ativa, troca para a última aba da lista
            if self.active_tab_id == tab_id:
                self._trocar_para_aba(self.tabs[-1]['id'])
            else:
                # Se não era a ativa, apenas atualiza a lista de abas no JS
                self._notificar_js_sobre_abas()

        def on_topbar_load_changed(self, webview, load_event):
            """Quando a topbar.html carregar, injeta os dados iniciais."""
            if load_event == WebKit2.LoadEvent.FINISHED:
                log(f"Topbar para {self.win_id} carregada. Inicializando com dados.")
                init_data = {
                    "win_id": self.win_id,
                    "tema": self.tema,
                    "favorites": self.favorites,
                    "collapsed": self.topbar_collapsed,
                    "tabs": [] # As abas serão enviadas separadamente
                }
                js_code = f"window.initializeTopbar({json.dumps(init_data)})"
                self.topbar_view.run_javascript(js_code, None, None, None)
                self._notificar_js_sobre_abas() # Envia a lista inicial de abas

        def on_content_load_changed(self, webview, load_event, tab):
            """Quando o conteúdo principal carregar, atualiza a URL na topbar."""
            if load_event == WebKit2.LoadEvent.FINISHED:
                uri = webview.get_uri() or ""
                log(f"Conteúdo para {self.win_id} carregado: {uri}. Atualizando topbar.")
                js_code = f"window.updateUrlAndTitle('{tab['id']}', '{uri}', '{tab['title']}')"
                self.topbar_view.run_javascript(js_code, None, None, None)

        def on_content_title_changed(self, webview, _, tab):
            """Quando o título do conteúdo principal mudar, atualiza o título da janela GTK e da taskbar."""
            new_title = webview.get_title() or "Nova Aba"
            tab['title'] = new_title

            # Se a aba que mudou de título é a ativa, atualiza o título da janela principal
            if tab['id'] == self.active_tab_id:
                self.set_title(new_title)
                # Notifica o JS principal para atualizar o botão na barra de tarefas
                titulo_escapado = new_title.replace("'", "\\'")
                self.main_app.send_js_command(f"updateNativeWindowTitle('{self.win_id}', '{titulo_escapado}')")
            
            # Notifica a topbar para atualizar o título no botão da aba
            uri = webview.get_uri() or ""
            js_code = f"window.updateUrlAndTitle('{tab['id']}', '{uri}', '{new_title.replace("'", "\\'")}')"
            self.topbar_view.run_javascript(js_code, None, None, None)

        def on_window_state_change(self, widget, event):
            if event.new_window_state & Gdk.WindowState.ICONIFIED:
                log(f"Janela {self.win_id} minimizada. Notificando JS.")
                self.main_app.send_js_command(f"navegadorMinimizado('{self.win_id}', '{self.get_title()}')")

        def on_enter_fullscreen(self, webview, _=None): # Adicionado _ para compatibilidade de sinal
            """
            Chamado quando o conteúdo da web (ex: vídeo do YouTube) entra em tela cheia.
            Oculta a nossa topbar customizada para uma experiência imersiva.
            """
            log(f"Janela {self.win_id} entrou em fullscreen. Ocultando topbar.")
            self.topbar_view.hide()
            return True # Indica que lidamos com o evento

        def on_leave_fullscreen(self, webview, _=None): # Adicionado _ para compatibilidade de sinal
            """
            Chamado quando o conteúdo da web sai da tela cheia.
            Mostra a nossa topbar customizada novamente.
            """
            log(f"Janela {self.win_id} saiu do fullscreen. Exibindo topbar.")
            self.topbar_view.show()
            return True # Indica que lidamos com o evento

        def on_dialog_message(self, manager, message):
            """Lida com mensagens vindas da WebView do diálogo."""
            try:
                data = json.loads(message.get_js_value().to_string())
                acao = data.get("acao")
                dados = data.get("dados", {})

                if acao == "dialog_result":
                    self.hide_favorite_dialog() # Fecha a UI do diálogo
                    if dados.get("result") == "confirm":
                        # Finaliza a adição do favorito chamando o JS da topbar
                        new_title = dados.get("newTitle")
                        url = dados.get("url")
                        js_code = f"window.finalizeFavoriteAdd({json.dumps({'newTitle': new_title, 'url': url})})"
                        self.topbar_view.run_javascript(js_code, None, None, None)
            except Exception as e:
                log(f"[ERRO] Mensagem do diálogo do navegador: {e}")

        def on_destroy_event(self, widget):
            log(f"Janela {self.win_id} fechada. Notificando JS.")
            self.main_app.send_js_command(f"navegadorFechado('{self.win_id}')")
            del self.main_app.open_windows[self.win_id] # Remove da lista de janelas ativas

    class WebAppWindow(Gtk.Window):
        """NOVO: Uma classe para a janela de WebApp com topbar simplificada."""
        def __init__(self, main_app, win_id, url, nome, tema, manager):
            super().__init__(title=nome)
            self.main_app = main_app
            self.win_id = win_id
            self.nome = nome
            self.url = url

            self.set_default_size(1024, 768)
            self.set_position(Gtk.WindowPosition.CENTER)
            self.set_decorated(False)

            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            self.add(box)

            # WebView para a Topbar simplificada
            self.topbar_view = WebKit2.WebView.new_with_user_content_manager(manager)
            self.topbar_view.set_size_request(-1, 40) # Altura menor
            self.topbar_view.connect("load-changed", self.on_topbar_load_changed)
            
            # WebView para o conteúdo do WebApp
            self.content_view = WebKit2.WebView.new_with_user_content_manager(manager)
            self.content_view.connect("notify::title", self.on_content_title_changed)

            box.pack_start(self.topbar_view, False, False, 0)
            box.pack_start(self.content_view, True, True, 0)

            topbar_path = self.main_app.base_dir / "webapp_topbar.html"
            
            # VALIDAÇÃO: Verifica se o arquivo da topbar existe. Se não, a janela não pode ser criada.
            if not topbar_path.is_file():
                log(f"[ERRO CRÍTICO] Não foi possível criar a janela do WebApp. Arquivo essencial não encontrado: {topbar_path}")
                # É importante destruir a janela para não deixar um processo 'fantasma' rodando.
                GLib.idle_add(self.destroy)
                return

            self.topbar_view.load_uri(f"file://{topbar_path}")
            self.content_view.load_uri(self.url)

            self.connect("destroy", self.on_destroy_event)
            
            # Aplica o tema
            settings = Gtk.Settings.get_default()
            is_dark_theme = not tema.endswith('-light')
            settings.set_property("gtk-application-prefer-dark-theme", is_dark_theme)

            self.show_all()
        
        def on_topbar_load_changed(self, webview, load_event):
            """Quando a webapp_topbar.html carregar, injeta os dados iniciais."""
            if load_event == WebKit2.LoadEvent.FINISHED:
                log(f"Topbar do WebApp {self.win_id} carregada. Inicializando com nome.")
                init_data = {"win_id": self.win_id, "nome": self.nome}
                js_code = f"window.initializeWebappTopbar({json.dumps(init_data)})"
                self.topbar_view.run_javascript(js_code, None, None, None)
        
        def on_content_title_changed(self, webview, _):
            """Quando o título do conteúdo do WebApp mudar, atualiza o título da janela GTK."""
            new_title = webview.get_title()
            if new_title: self.set_title(f"{self.nome} - {new_title}")
            else: self.set_title(self.nome)

        def on_destroy_event(self, widget):
            log(f"Janela {self.win_id} fechada. Notificando JS.")
            self.main_app.send_js_command(f"navegadorFechado('{self.win_id}')")
            if self.win_id in self.main_app.open_windows:
                del self.main_app.open_windows[self.win_id]

    class AppGTK:
        def __init__(self):
            log("Inicializando em modo GTK...")
            
            # NOVO: Log para depuração da versão do WebKitGTK
            major = WebKit2.get_major_version()
            minor = WebKit2.get_minor_version()
            micro = WebKit2.get_micro_version()
            log(f"Usando WebKit2GTK versão: {major}.{minor}.{micro}")
            # NOVO: Log de variáveis de ambiente D-Bus para depuração
            log(f"DBUS_SESSION_BUS_ADDRESS: {os.environ.get('DBUS_SESSION_BUS_ADDRESS')}")
            log(f"XDG_SESSION_ID: {os.environ.get('XDG_SESSION_ID')}")
            log(f"XDG_RUNTIME_DIR: {os.environ.get('XDG_RUNTIME_DIR')}")

            ### CORREÇÃO 1/2: Definir um nome de aplicativo. ###
            # Isto é ESSENCIAL. O sistema operacional (via xdg-desktop-portal)
            # precisa de um nome único para saber quem está pedindo permissão
            # para gravar a tela. Sem isso, ele nega o pedido por segurança.
            GLib.set_application_name("com.raijinforge.vortexobs")

            self.current_theme = "vortex-dark" # Atributo para armazenar o tema atual

            self.base_dir = Path(sys.argv[0]).resolve().parent
            self.open_windows = {}
            self.next_win_id = 0
            self.window = Gtk.Window(title="Vortex-IDE")
            
            # NOVO: Detecta a resolução e define o tamanho da janela em vez de usar fullscreen.
            # Isso é mais compatível com diferentes gerenciadores de janela e ambientes.
            screen = self.window.get_screen()
            width = screen.get_width()
            height = screen.get_height()
            self.window.set_default_size(width, height)
            log(f"Definindo tamanho da janela para a resolução da tela: {width}x{height}")

            self.window.set_decorated(False)
            self.window.set_app_paintable(True)
            screen = self.window.get_screen()
            visual = screen.get_rgba_visual()
            if visual and screen.is_composited():
                self.window.set_visual(visual)
                log("Janela com visual RGBA ativado (transparência + arredondamento ok)")
            else:
                log("[Aviso] Visual RGBA não suportado — cantos arredondados podem não funcionar.")
            self.window.connect("destroy", Gtk.main_quit)
            self.manager = WebKit2.UserContentManager()
            self.manager.register_script_message_handler("bridge")
            self.manager.connect("script-message-received::bridge", self.on_js_message)

            self.webview = WebKit2.WebView.new_with_user_content_manager(self.manager)
            
            ### CORREÇÃO 2/2: Conectar o manipulador de permissões. ###
            self.webview.connect("permission-request", self.on_permission_request)

            self.webview.set_background_color(Gdk.RGBA(0, 0, 0, 0))

            # --- Otimizações de Performance e QUALIDADE para WebKit2GTK ---
            settings = self.webview.get_settings()

            # 1. Aceleração por Hardware: A mais importante. Força o uso da GPU para renderização.
            # Isso melhora drasticamente a qualidade do anti-aliasing de fontes no canvas.
            if hasattr(settings, "set_hardware_acceleration_policy"):
                settings.set_hardware_acceleration_policy(WebKit2.HardwareAccelerationPolicy.ALWAYS)

            # 2. JIT para JavaScript: Acelera a execução de scripts.
            if hasattr(settings, "set_enable_jsc_jit"):
                settings.set_enable_jsc_jit(True)

            # 3. Composição em Threads: Melhora a fluidez geral da renderização.
            if hasattr(settings, "set_enable_threaded_compositing"):
                settings.set_enable_threaded_compositing(True)

            # 4. WebGL e Canvas 2D Acelerado: Essencial para apps com gráficos e crucial para a qualidade do seu editor.
            settings.set_enable_webgl(True)
            settings.set_enable_accelerated_2d_canvas(True)

            settings.set_enable_javascript(True)
            settings.set_enable_media_stream(True)
            settings.set_enable_smooth_scrolling(True)
            settings.set_enable_webaudio(True)
            settings.set_allow_file_access_from_file_urls(True)
            # NOVO: Habilita o Inspetor Web (Ferramentas de Desenvolvedor)
            # Clique com o botão direito -> Inspecionar Elemento para abrir.
            # Essencial para depurar performance do frontend.
            settings.set_enable_developer_extras(True)

            modern_user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) appleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
            settings.set_user_agent(modern_user_agent)

            index_path = self.base_dir / "desktop.html"
            self.webview.load_uri(f"file://{index_path}")
            self.window.add(self.webview)

            self.window.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
            
            self.window.show_all()

            self.executor = ThreadPoolExecutor(max_workers=5)

        ### CORREÇÃO 2/2: A função que lida com as permissões. ###
        def on_permission_request(self, webview, request):
            """
            Manipula os pedidos de permissão da WebView.
            Esta é a parte mais importante da correção.
            """
            log(f"Recebido pedido de permissão do tipo: {type(request)}")

            # NOVO: Lida especificamente com o pedido de enumeração de dispositivos.
            # O log mostrou que este é o primeiro tipo de pedido que o getDisplayMedia faz.
            # Ao permitir diretamente aqui, evitamos uma chamada ao portal que estava falhando.
            if isinstance(request, WebKit2.DeviceInfoPermissionRequest):
                log("Permissão de DeviceInfo (enumeração) solicitada. Permitindo...")
                request.allow()
                return True # Diz ao WebKit que já lidamos com este pedido.

            # Se o pedido for para microfone/câmera (getUserMedia), nós o aprovamos.
            # É por isso que seu microfone já funcionava.
            if isinstance(request, WebKit2.UserMediaPermissionRequest):
                log("Permissão de UserMedia (microfone/câmera) solicitada. Permitindo...")
                request.allow()
                return True # Diz ao WebKit que nós já lidamos com este pedido.

            # Se o pedido for para QUALQUER OUTRA COISA (incluindo a gravação de tela,
            # que é um WebKit2.PermissionRequest), nós retornamos False.
            # Retornar False diz ao WebKit: "Eu não sei como lidar com isso, use o seu
            # (xdg-desktop-portal), que irá mostrar o diálogo nativo para o usuário.
            log("Pedido de permissão não é de UserMedia/DeviceInfo. Deixando o sistema (portal) lidar com isso.")
            return False

        def on_js_message(self, manager, message):
            try:
                data = json.loads(message.get_js_value().to_string())
                acao = data.get("acao")
                dados = data.get("dados", {})
                req_id = data.get("req_id")
                log(f"[GTK] Ação recebida: {acao} (req_id: {req_id})")

                # Tratamento especial para 'abrir_arquivo_padrao'
                if acao == "abrir_arquivo_padrao":
                    # Chama o handler para determinar a ação real. É rápido, então pode ser na thread principal.
                    resultado_handler = handler.abrir_arquivo_padrao(dados)
                    
                    if "erro" in resultado_handler:
                        resultado_handler["req_id"] = req_id
                        GLib.idle_add(self.run_js_response, resultado_handler)
                        return

                    if "saida" in resultado_handler and isinstance(resultado_handler["saida"], dict) and "acao" in resultado_handler["saida"]:
                        sub_acao = resultado_handler["saida"]["acao"]
                        sub_dados = resultado_handler["saida"]["dados"]
                        
                        # Se for para abrir um webapp, executa na thread da UI.
                        if sub_acao == "abrir_webapp":
                            GLib.idle_add(lambda: self.executar_acao_main_thread_interativa(sub_acao, sub_dados, req_id))
                            # Envia uma resposta de sucesso genérica para o JS não ficar esperando
                            GLib.idle_add(self.run_js_response, {"saida": {"acao": "backend_handled"}, "req_id": req_id})
                        else:
                            # Para outros tipos de arquivo, envia a resposta completa para o JS.
                            resultado_handler["req_id"] = req_id
                            GLib.idle_add(self.run_js_response, resultado_handler)
                    else:
                        # Se o handler não retornou uma sub-ação, envia a resposta como está.
                        resultado_handler["req_id"] = req_id
                        GLib.idle_add(self.run_js_response, resultado_handler)
                    return # Finaliza o processamento aqui.

                # Lista de ações que PRECISAM rodar na thread principal da UI
                acoes_interativas = [
                    "abrir_navegador", "restaurar_janela", "controlar_janela_nativa", "arrastar_janela_nativa", "set_topbar_state", "navegador_iniciar_redimensionamento", "get_current_page_title",
                    "navegador_nova_aba", "navegador_trocar_aba", "navegador_fechar_aba",
                    "navegador_voltar", "navegador_avancar", "navegador_ir_para_url", "request_favorite_name_dialog",
                    "export_to_pdf",
                    "salvar_favoritos_navegador" # << ESSENCIAL: Mover para cá
                ]

                if acao in acoes_interativas:
                    GLib.idle_add(lambda: self.executar_acao_main_thread_interativa(acao, dados, req_id))
                else:
                    future = self.executor.submit(
                        executar_acao_background, acao, dados, req_id, self.send_progress_to_js
                    )
                    future.add_done_callback(lambda f: self.on_task_done(f, req_id))

            except Exception as e:
                log(f"[ERRO] GTK JS handler: {e}")
                resposta = {"erro": str(e), "req_id": data.get("req_id")}
                self.run_js_response(resposta)

        def send_js_command(self, js_code):
            """ Roda um comando JS na WebView principal. """
            GLib.idle_add(self.webview.run_javascript, js_code, None, None, None)

        def send_progress_to_js(self, data):
            GLib.idle_add(self.run_js_response, data)
            return GLib.SOURCE_REMOVE

        def executar_acao_main_thread_interativa(self, acao, dados, req_id):
            log(f"Executando ação interativa na thread principal (GTK): {acao}")
            resultado = {"sucesso": True, "acao": acao} # Resposta padrão
            match acao:
                case "abrir_navegador":
                    self.abrir_navegador_gtk(dados)
                case "abrir_webapp":
                    win_id = f"native_{self.next_win_id}"
                    self.next_win_id += 1
                    
                    url = dados.get("url")
                    nome = dados.get("name")

                    # VALIDAÇÃO: Garante que os dados do WebApp são válidos antes de prosseguir.
                    # A falta de 'nome' ou 'url' pode causar um erro silencioso.
                    if not nome or not url:
                        log(f"[ERRO] Tentativa de abrir WebApp com dados inválidos. Nome: '{nome}', URL: '{url}'. Dados completos: {dados}")
                        # Opcional: Enviar um erro de volta para o JS, se houver req_id
                        if req_id:
                            self.run_js_response({"erro": f"Dados do WebApp '{nome or 'desconhecido'}' estão corrompidos ou ausentes.", "req_id": req_id})
                        return # Aborta a operação

                    log(f"Abrindo WebApp '{nome}' em uma janela nativa com URL: {url}")
                    tema = self.current_theme

                    nova_janela = WebAppWindow(self, win_id, url, nome, tema, self.manager)
                    self.open_windows[win_id] = nova_janela
                    
                    titulo_escapado = nome.replace("'", "\\'")
                    self.send_js_command(f"navegadorAberto('{win_id}', '{titulo_escapado}')")
                    # CORREÇÃO: Impede que uma segunda resposta seja enviada para a mesma requisição.
                    # A resposta 'backend_handled' já foi enviada pelo on_js_message.
                    return
                case "export_to_pdf":
                    if not WEASYPRINT_OK:
                        resultado = {"sucesso": False, "erro": "A biblioteca 'weasyprint' é necessária, mas não foi encontrada."}
                    else:
                        html_content = dados.get("html")
                        filepath = dados.get("filepath")
                        if not html_content or not filepath:
                            resultado = {"sucesso": False, "erro": "Conteúdo HTML ou caminho do arquivo não fornecido."}
                        else:
                            try:
                                HTML(string=html_content, base_url=str(self.base_dir)).write_pdf(filepath)
                                resultado = {"sucesso": True, "saida": f"PDF salvo em {filepath}"}
                            except Exception as e:
                                log(f"[ERRO] Falha ao gerar PDF: {e}")
                                resultado = {"sucesso": False, "erro": f"Erro ao gerar PDF: {e}"}
                case "arrastar_janela_nativa":
                    self.iniciar_arrasto_janela_nativa(dados)
                case "restaurar_janela":
                    win_id = dados.get("win_id")
                    if win_id in self.open_windows:
                        self.open_windows[win_id].present()
                    else:
                        resultado = {"sucesso": False, "erro": f"Janela {win_id} não encontrada."}
                case "controlar_janela_nativa":
                    win_id = dados.get("win_id")
                    comando = dados.get("comando")
                    if win_id in self.open_windows:
                        window = self.open_windows[win_id]
                        if comando == "fechar": window.close()
                        elif comando == "minimizar": window.iconify()
                        elif comando == "maximizar":
                            if window.is_maximized(): window.unmaximize()
                            else: window.maximize()
                        else:
                             resultado = {"sucesso": False, "erro": f"Comando desconhecido: {comando}"}
                    else:
                        resultado = {"sucesso": False, "erro": f"Janela {win_id} não encontrada."}
                case "set_topbar_state":
                    win_id = dados.get("win_id")
                    collapsed = dados.get("collapsed", False)
                    if win_id in self.open_windows:
                        self.open_windows[win_id].topbar_collapsed = collapsed
                case "salvar_favoritos_navegador":
                    win_id = dados.get("win_id")
                    new_favorites = dados.get("favoritos", [])
                    if win_id in self.open_windows:
                        self.open_windows[win_id].favorites = new_favorites
                    self.executor.submit(handler.salvar_favoritos_navegador, dados.copy())
                    resultado["saida"] = "Comando de salvar recebido."
                case "navegador_iniciar_redimensionamento":
                    win_id = dados.get("win_id")
                    edge_str = dados.get("edge")
                    screen_x = dados.get("screenX")
                    screen_y = dados.get("screenY")
                    if win_id in self.open_windows and all(k is not None for k in [edge_str, screen_x, screen_y]):
                        window = self.open_windows[win_id]
                        edge_map = {
                            "north_west": Gdk.WindowEdge.NORTH_WEST, "north": Gdk.WindowEdge.NORTH, "north_east": Gdk.WindowEdge.NORTH_EAST,
                            "west": Gdk.WindowEdge.WEST, "east": Gdk.WindowEdge.EAST,
                            "south_west": Gdk.WindowEdge.SOUTH_WEST, "south": Gdk.WindowEdge.SOUTH, "south_east": Gdk.WindowEdge.SOUTH_EAST,
                        }
                        gdk_edge = edge_map.get(edge_str)
                        if gdk_edge is not None:
                            window.begin_resize_drag(gdk_edge, 1, screen_x, screen_y, Gtk.get_current_event_time())
                case "get_current_page_title":
                    win_id = dados.get("win_id")
                    if win_id in self.open_windows:
                        window = self.open_windows[win_id]
                        active_tab = window._get_tab_by_id(window.active_tab_id)
                        if active_tab:
                            title = active_tab['view'].get_title() or ""
                            title_escaped = title.replace("'", "\\'")
                            js_code = f"window.receivePageTitleForFavorite('{title_escaped}')"
                            window.topbar_view.run_javascript(js_code, None, None, None)
                case "request_favorite_name_dialog":
                    win_id = dados.get("win_id")
                    url = dados.get("url")
                    default_name = dados.get("defaultName")
                    if win_id in self.open_windows:
                        self.open_windows[win_id].show_favorite_dialog(url, default_name)
                    else:
                        log(f"[ERRO] Janela do navegador '{win_id}' não encontrada para mostrar diálogo.")
                case "navegador_nova_aba":
                    win_id = dados.get("win_id")
                    if win_id in self.open_windows:
                        self.open_windows[win_id]._criar_nova_aba()
                case "navegador_trocar_aba":
                    win_id = dados.get("win_id")
                    tab_id = dados.get("tab_id")
                    if win_id in self.open_windows:
                        self.open_windows[win_id]._trocar_para_aba(tab_id)
                case "navegador_fechar_aba":
                    win_id = dados.get("win_id")
                    tab_id = dados.get("tab_id")
                    if win_id in self.open_windows:
                        self.open_windows[win_id]._fechar_aba(tab_id)
                case "navegador_voltar":
                    win_id = dados.get("win_id")
                    if win_id in self.open_windows:
                        active_tab = self.open_windows[win_id]._get_tab_by_id(self.open_windows[win_id].active_tab_id)
                        if active_tab: active_tab['view'].go_back()
                case "navegador_avancar":
                    win_id = dados.get("win_id")
                    if win_id in self.open_windows:
                        active_tab = self.open_windows[win_id]._get_tab_by_id(self.open_windows[win_id].active_tab_id)
                        if active_tab: active_tab['view'].go_forward()
                case "navegador_ir_para_url":
                    win_id = dados.get("win_id")
                    url = dados.get("url")
                    if win_id in self.open_windows and url:
                        active_tab = self.open_windows[win_id]._get_tab_by_id(self.open_windows[win_id].active_tab_id)
                        if not (url.startswith("http://") or url.startswith("https://")):
                            url = "https://" + url
                        if active_tab: active_tab['view'].load_uri(url)
                case _:
                    resultado = {"sucesso": False, "erro": f"Ação interativa desconhecida: {acao}"}
            
            # Apenas envia uma resposta se houver um req_id, para não poluir o JS
            if req_id:
                resultado["req_id"] = req_id
                self.run_js_response(resultado)
            
            return GLib.SOURCE_REMOVE
            
        def on_task_done(self, future, req_id):
            try:
                resultado = future.result()
                resultado["req_id"] = req_id
            except Exception as e:
                log(f"[ERRO] Erro na tarefa assíncrona: {e}")
                resultado = {"erro": str(e), "req_id": req_id}
            
            GLib.idle_add(self.run_js_response, resultado)

        def abrir_navegador_gtk(self, dados):
            """Cria e gerencia uma nova janela de navegador nativa."""
            url = dados.get("url", "https://google.com")
            tema = dados.get("tema", "dark")
            win_id = f"native_{self.next_win_id}"
            self.current_theme = tema # Atualiza o tema atual da aplicação
            self.next_win_id += 1

            log(f"Abrindo janela de navegador GTK com ID {win_id} para URL: {url}")
            
            nova_janela = NavegadorWindow(self, win_id, url, tema, self.manager)
            self.open_windows[win_id] = nova_janela

            # NOVO: Carrega os favoritos e os atribui à nova instância da janela
            fav_data = handler.carregar_favoritos_navegador()
            nova_janela.favorites = fav_data.get('saida', [])
            log(f"Favoritos carregados para a nova janela {win_id}: {len(nova_janela.favorites)} itens.")

            # NOVO: Envia comando para o JS criar o botão na taskbar imediatamente
            titulo = nova_janela.get_title()
            titulo_escapado = titulo.replace("'", "\\'") # Escapa aspas para segurança
            self.send_js_command(f"navegadorAberto('{win_id}', '{titulo_escapado}')")

        def handle_export_to_pdf(self, dados):
            """Abre um diálogo para salvar e, se confirmado, gera o PDF."""
            html_content = dados.get("html")
            default_filename = dados.get("filename", "documento.pdf")

            if not html_content:
                return {"sucesso": False, "erro": "Nenhum conteúdo HTML recebido para gerar o PDF."}

            dialog = Gtk.FileChooserDialog(
                title="Exportar como PDF",
                parent=self.window,
                action=Gtk.FileChooserAction.SAVE
            )
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            dialog.set_do_overwrite_confirmation(True)
            dialog.set_current_name(default_filename)

            pdf_filter = Gtk.FileFilter()
            pdf_filter.set_name("Arquivos PDF")
            pdf_filter.add_mime_type("application/pdf")
            pdf_filter.add_pattern("*.pdf")
            dialog.add_filter(pdf_filter)

            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                filepath = dialog.get_filename()
                dialog.destroy()
                if not filepath.lower().endswith('.pdf'):
                    filepath += '.pdf'
                try:
                    HTML(string=html_content).write_pdf(filepath)
                    return {"sucesso": True, "saida": f"PDF salvo em {filepath}"}
                except Exception as e:
                    return {"sucesso": False, "erro": f"Erro ao gerar PDF: {e}"}
            else:
                dialog.destroy()
                return {"sucesso": False, "saida": "Exportação cancelada."}

        def run_js_response(self, resposta):
            js_code = f"handleNodeResponse({json.dumps(resposta)});"
            self.webview.run_javascript(js_code, None, None, None)
            return GLib.SOURCE_REMOVE

        def iniciar_arrasto_janela_nativa(self, dados):
            win_id = dados.get("win_id")
            if win_id not in self.open_windows:
                log(f"[ERRO] Tentativa de arrastar janela nativa inexistente: {win_id}")
                return

            window = self.open_windows[win_id]
            # Usa as coordenadas precisas recebidas do JavaScript
            screen_x = dados.get("screenX")
            screen_y = dados.get("screenY")
            
            if screen_x is not None and screen_y is not None:
                current_time = Gtk.get_current_event_time()
                window.begin_move_drag(1, screen_x, screen_y, current_time)
                log(f"Arrasto da janela nativa {win_id} iniciado com coords ({screen_x}, {screen_y}).")
            else:
                log(f"[ERRO] Coordenadas de arrasto não recebidas do JS para a janela {win_id}.")

        def iniciar_arrasto_simulado_via_js(self, req_id):
            log("Ação 'arrastar_janela' recebida via JS. Iniciando arrasto simulado.")
            try:
                display = Gdk.Display.get_default()
                if display:
                    screen_x, screen_y, _ = display.get_pointer()
                    current_time = Gtk.get_current_event_time()

                    self.window.begin_move_drag(
                        1,  # Botão 1 (esquerdo do mouse)
                        screen_x,
                        screen_y,
                        current_time
                    )
                    log("Arrasto da janela iniciado com sucesso via JS.")
                    resposta = {"sucesso": True, "acao": "arrastar_janela", "req_id": req_id}
                else:
                    log("[ERRO] Não foi possível obter o display Gdk para arrasto simulado.")
                    resposta = {"erro": "Não foi possível arrastar (Gdk display not found).", "req_id": req_id}

            except Exception as e:
                log(f"[ERRO] Falha ao arrastar a janela via JS: {e}")
                resposta = {"erro": f"Erro ao arrastar: {e}", "req_id": req_id}
            
            self.run_js_response(resposta)
            return GLib.SOURCE_REMOVE

    # A função executar_acao_background agora recebe o req_id
    def executar_acao_background(acao, dados, req_id_do_js, send_callback_func=None):
        # Garante que o req_id esteja nos dados antes de passar para o handler
        dados["req_id"] = req_id_do_js 
        log(f"Executando ação em background: {acao} (req_id: {req_id_do_js})")
        match acao:
            case "executar_shell": return handler.executar_shell(dados)
            case "executar_script": return handler.executar_script(dados)
            case "executar_script_dir_arg": return handler.executar_script_dir_arg(dados, send_callback=send_callback_func)
            case "baixar_com_wget": return handler.baixar_com_wget(dados, send_callback=send_callback_func)
            case "salvar_arquivo": return handler.salvar_arquivo(dados)
            case "abrir_imagem": return handler.abrir_imagem(dados)
            case "abrir_img_dir": return handler.abrir_img_dir(dados)
            case "executar_script_parametro": return handler.executar_script_parametro(dados)
            case "listar_variaveis": return handler.listar_variaveis()
            case "pegar_apps": return handler.pegar_apps(dados)
            case "pegar_instalado": return handler.pegar_instalado(dados)
            case "salvar_instalado": return handler.salvar_instalado(dados)
            case "salvar_modo": return handler.salvar_modo(dados)
            case "pegar_tema": return handler.pegar_tema(dados)
            case "remover_instalado": return handler.remover_instalado(dados)
            case "verificar_instalado": return handler.verificar_instalado(dados)
            case "escolher_arquivo": return handler.escolher_arquivo(dados)
            case "copiar_arquivo": return handler.copiar_arquivo(dados)
            case "carregar_projeto": return handler.carregar_projeto(dados)
            case "portar_base": return handler.portar_base(dados)
            case "gerar_appimage": return handler.gerar_appimage(dados)
            case "listar_conteudo_diretorio": return handler.listar_conteudo_diretorio(dados)
            case "abrir_arquivo_padrao": return handler.abrir_arquivo_padrao(dados)
            case "mover_item": return handler.mover_item(dados)
            case "mover_itens_para_pasta": return handler.mover_itens_para_pasta(dados)
            case "excluir_item": return handler.excluir_item(dados)
            case "criar_pasta": return handler.criar_pasta(dados)
            case "renomear_item": return handler.renomear_item(dados)
            case "listar_imagens_galeria": return handler.listar_imagens_galeria(dados)
            case "listar_papeis_de_parede": return handler.listar_papeis_de_parede(dados)
            case "ler_arquivo_como_base64": return handler.ler_arquivo_como_base64(dados)
            case "copiar_item": return handler.copiar_item(dados)
            case "ler_arquivo_texto": return handler.ler_arquivo_texto(dados)
            case "get_system_volume": return handler.get_system_volume(dados)
            case "set_system_volume": return handler.set_system_volume(dados)
            case "get_system_stats": return handler.get_system_stats(dados)
            case "system_shutdown": return handler.system_shutdown(dados)
            case "system_reboot": return handler.system_reboot(dados)
            case "system_logout": return handler.system_logout(dados)
            case "listar_vortex_apps": return handler.listar_vortex_apps(dados)
            case "listar_icones_desktop": return handler.listar_icones_desktop(dados)
            case "criar_pasta_desktop": return handler.criar_pasta_desktop(dados)
            case "get_weather_forecast": return handler.get_weather_forecast(dados)
            case "salvar_arquivo_base64": return handler.salvar_arquivo_base64(dados)
            case "listar_icones_disponiveis": return handler.listar_icones_disponiveis(dados)
            case "salvar_icone_menu": return handler.salvar_icone_menu(dados)
            case "carregar_icone_menu": return handler.carregar_icone_menu(dados)
            case "copiar_icone_usuario": return handler.copiar_icone_usuario(dados)
            case "salvar_icones_poder": return handler.salvar_icones_poder(dados)
            case "carregar_icones_poder": return handler.carregar_icones_poder(dados)
            case "criar_webapp_atalho": return handler.criar_webapp_atalho(dados)
            case "criar_atalho_desktop": return handler.criar_atalho_desktop(dados)
            case "get_desktop_path": return handler.get_desktop_path(dados)
            case "add_to_recent_apps": return handler.add_to_recent_apps(dados)
            case "get_recent_apps": return handler.get_recent_apps(dados)
            case "add_to_recent_files": return handler.add_to_recent_files(dados)
            case "get_recent_files": return handler.get_recent_files(dados)
            case "salvar_apps_fixados": return handler.salvar_apps_fixados(dados)
            case "carregar_apps_fixados": return handler.carregar_apps_fixados(dados)
            case "salvar_layout_menu": return handler.salvar_layout_menu(dados)
            case "carregar_layout_menu": return handler.carregar_layout_menu(dados) #NOSONAR
            case "carregar_favoritos_navegador": return handler.carregar_favoritos_navegador(dados)
            case "carregar_desktop_theme": return handler.carregar_desktop_theme(dados)
            case "salvar_desktop_theme": return handler.salvar_desktop_theme(dados)
            case "salvar_widgets_config": return handler.salvar_widgets_config(dados)
            case "carregar_widgets_config": return handler.carregar_widgets_config(dados)
            case "salvar_wallpaper_config": return handler.salvar_wallpaper_config(dados)
            case "carregar_wallpaper_config": return handler.carregar_wallpaper_config(dados)
            # NOVO: Handlers do Calendário
            case "salvar_eventos_calendario": return handler.salvar_eventos_calendario(dados)
            case "carregar_eventos_calendario": return handler.carregar_eventos_calendario(dados)
            # NOVO: Handlers de Mídia
            case "get_media_status": return handler.get_media_status(dados)
            case "control_media_player": return handler.control_media_player(dados)
            case "get_special_folder_path": return handler.get_special_folder_path(dados)
            case "get_item_details": return handler.get_item_details(dados)
            case "get_item_properties": return handler.get_item_properties(dados)
            case "executar_comando_vortex": return handler.executar_comando_vortex(dados)
            case "resolve_path": return handler.resolve_path(dados)
            case "autocomplete_path": return handler.autocomplete_path(dados)
            case _: return {"erro": f"Ação desconhecida: {acao}"}

    AppGTK()
    Gtk.main()

if __name__ == "__main__":
    # 1. Garante que o Tkinter (para os diálogos de erro/instalação) esteja disponível
    if not verificar_tk_instalado_ou_instalar():
        # A função já loga o erro, então apenas saímos.
        sys.exit(1)

    # 2. Verifica e instala dependências pip (como psutil) a partir de requirements.txt
    if not verificar_e_instalar_dependencias_pip():
        sys.exit("Dependências pip não foram satisfeitas. Encerrando.")

    # 3. Continua com a verificação de dependências do sistema (GTK/WebKit)
    ambiente = detectar_ambiente()
    versao_gtk = dependencias_ok(ambiente)

    if versao_gtk:
        iniciar_gtk(versao_gtk)
    else:
        log("Dependências de sistema (GTK/WebKit) faltando. Abrindo instalador embutido...")
        chamar_instalador_embutido()
