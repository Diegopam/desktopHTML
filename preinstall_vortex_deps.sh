#!/bin/bash

# ==============================================================================
# Script de Instalação de Dependências e Deploy do Vortex Desktop
# ==============================================================================
# Este script realiza a instalação completa do Vortex Desktop em nível de sistema.
# 1. Instala dependências (incluindo LightDM)
# 2. Instala o software em /opt/vortexDesktop
# 3. Cria binários e entradas de sessão
#
# Suporta: Debian/Ubuntu (apt), Arch Linux (pacman), Fedora (dnf), openSUSE (zypper)
# ==============================================================================

# --- Configurações ---
LOG_FILE="vortex_install.log"
INSTALL_DIR="/opt/vortexDesktop"
BIN_WRAPPER="/usr/bin/start-vortex"
SESSION_FILE="/usr/share/xsessions/vortex.desktop"
VORTEX_URL="https://github.com/Diegopam/desktopHTML/releases/download/FINAL-1.1.3/vtxDesktop.tar.gz"
DISTRO=""
PKG_MANAGER=""
DOWNLOAD_CMD=""

# Definição de pacotes por distribuição
declare -A PACKAGES=(
    # Debian/Ubuntu (apt)
    [apt]="xorg lightdm pulseaudio fonts-noto-color-emoji fontconfig libgtk-3-dev libwebkit2gtk-4.0-dev python3 python3-pip python3-gi python3-tk python3-xlib python3-dbus playerctl jq curl rsync policykit-1 openbox gnome-screenshot gir1.2-gtk-3.0 gir1.2-webkit2-4.0"
    
    # Arch Linux (pacman)
    [pacman]="xorg-server lightdm lightdm-gtk-greeter pulseaudio noto-fonts-emoji fontconfig gtk3 webkit2gtk python python-pip python-gobject python-tk python-xlib python-dbus playerctl jq curl rsync polkit openbox gnome-screenshot"
    
    # Fedora (dnf)
    [dnf]="xorg-x11-server-Xorg lightdm lightdm-gtk pulseaudio google-noto-emoji-fonts fontconfig gtk3-devel webkit2gtk4.0-devel python3 python3-pip python3-gobject python3-tkinter python3-xlib python3-dbus playerctl jq curl rsync polkit openbox gnome-screenshot"
    
    # openSUSE (zypper)
    [zypper]="xorg-x11-server lightdm pulseaudio noto-coloremoji-fonts fontconfig gtk3-devel webkit2gtk3-devel python3 python3-pip python3-gobject python3-tk python3-xlib python3-dbus playerctl jq curl rsync polkit openbox gnome-screenshot typelib-1_0-Gtk-3_0 typelib-1_0-WebKit2-4_0"
)

REQUIRED_PIP_PACKAGES=(
    "psutil"                # Utilidades de sistema (CPU, memória)
    "requests"              # Requisições HTTP
    "beautifulsoup4"        # Parse HTML/XML
    "weasyprint"            # Geração de PDF
)

# --- Funções de Log ---
log_info() { echo "[INFO] $1" | tee -a "$LOG_FILE"; }
log_success() { echo -e "\e[32m[SUCESSO]\e[0m $1" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "\e[33m[AVISO]\e[0m $1" | tee -a "$LOG_FILE"; }
log_error() { echo -e "\e[31m[ERRO]\e[0m $1" | tee -a "$LOG_FILE"; exit 1; }

# --- Detecção de Distribuição ---
detect_distro() {
    log_info "Detectando distribuição Linux..."
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        case $DISTRO in
            ubuntu|debian|linuxmint|pop|elementary|kali) PKG_MANAGER="apt" ;;
            arch|manjaro|endeavouros|garuda) PKG_MANAGER="pacman" ;;
            fedora|rhel|centos|rocky|almalinux) PKG_MANAGER="dnf" ;;
            opensuse*|sles) PKG_MANAGER="zypper" ;;
            *) log_error "Distribuição '$DISTRO' não suportada oficialmente." ;;
        esac
        log_info "Distro: $NAME ($PKG_MANAGER)"
    else
        log_error "Não foi possível detectar a distribuição."
    fi
}

# --- Verificações Iniciais ---
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Execute como root (sudo bash $0)."
    fi
}

# --- Verificar Ferramenta de Download ---
ensure_download_tool() {
    log_info "Verificando ferramenta de download..."
    
    if command -v curl >/dev/null 2>&1; then
        DOWNLOAD_CMD="curl -L -o"
        log_info "Usando: curl"
    elif command -v wget >/dev/null 2>&1; then
        DOWNLOAD_CMD="wget -O"
        log_info "Usando: wget"
    else
        log_warning "Nem curl nem wget foram encontrados."
        read -p "Deseja instalar o curl agora? (s/n): " choice
        if [[ "$choice" =~ ^[Ss]$ ]]; then
            log_info "Instalando curl..."
            case $PKG_MANAGER in
                apt) apt install -y curl >> "$LOG_FILE" 2>&1 ;;
                pacman) pacman -S --noconfirm curl >> "$LOG_FILE" 2>&1 ;;
                dnf) dnf install -y curl >> "$LOG_FILE" 2>&1 ;;
                zypper) zypper install -y curl >> "$LOG_FILE" 2>&1 ;;
            esac
            DOWNLOAD_CMD="curl -L -o"
            
            # Verifica se instalou corretamente
            if ! command -v curl >/dev/null 2>&1; then
                log_error "Falha ao instalar curl. Instale manualmente e tente novamente."
            fi
        else
            log_error "É necessária uma ferramenta de download para continuar."
        fi
    fi
}

# --- Instalação de Pacotes ---
install_packages() {
    local packages="${PACKAGES[$PKG_MANAGER]}"
    log_info "Instalando pacotes via $PKG_MANAGER..."
    
    case $PKG_MANAGER in
        apt)
            apt update -y >> "$LOG_FILE" 2>&1
            apt install -y $packages >> "$LOG_FILE" 2>&1 || log_error "Falha no apt install"
            ;;
        pacman)
            pacman -Syu --noconfirm >> "$LOG_FILE" 2>&1
            pacman -S --needed --noconfirm $packages >> "$LOG_FILE" 2>&1 || log_error "Falha no pacman"
            ;;
        dnf)
            dnf install -y $packages >> "$LOG_FILE" 2>&1 || log_error "Falha no dnf"
            ;;
        zypper)
            zypper install -y $packages >> "$LOG_FILE" 2>&1 || log_error "Falha no zypper"
            ;;
    esac
    log_success "Pacotes de sistema instalados."
}

# --- Instalação PIP ---
install_pip_packages() {
    log_info "Instalando dependências Python..."
    for pkg in "${REQUIRED_PIP_PACKAGES[@]}"; do
        if ! python3 -c "import $pkg" > /dev/null 2>&1; then
            python3 -m pip install --no-cache-dir --break-system-packages "$pkg" >> "$LOG_FILE" 2>&1 || log_warning "Falha ao instalar $pkg (pode já existir no sistema)"
        fi
    done
    log_success "Dependências Python verificadas."
}

# --- Instalação do Vortex (Download & Deploy) ---
install_vortex_system() {
    log_info "Preparando instalação em $INSTALL_DIR..."
    
    ensure_download_tool

    # Criar diretório limpo
    if [ -d "$INSTALL_DIR" ]; then
        log_warning "Diretório $INSTALL_DIR já existe. Fazendo backup..."
        mv "$INSTALL_DIR" "${INSTALL_DIR}_backup_$(date +%s)"
    fi
    mkdir -p "$INSTALL_DIR"
    
    # Download
    log_info "Baixando Vortex Desktop..."
    log_info "URL: $VORTEX_URL"
    
    if $DOWNLOAD_CMD "/tmp/vtxDesktop.tar.gz" "$VORTEX_URL"; then
        log_success "Download concluído."
    else
        log_error "Falha ao baixar o arquivo. Verifique sua conexão."
    fi
    
    # Extração
    log_info "Extraindo arquivos..."
    # --strip-components=1 remove a pasta raiz do tar.gz (se houver vtxDesktop/) para jogar os arquivos direto em /opt/vortexDesktop
    # Caso o tar.gz não tenha pasta raiz, remova essa flag. Assumindo estrutura padrão de release.
    if tar -xzf "/tmp/vtxDesktop.tar.gz" -C "$INSTALL_DIR"; then
        log_success "Arquivos extraídos."
    else
        log_error "Falha na extração do arquivo."
    fi
    
    # Limpeza
    rm -f "/tmp/vtxDesktop.tar.gz"
    
    # Ajustar permissões
    chmod +x "$INSTALL_DIR/run.sh"
    chmod +x "$INSTALL_DIR/main.py"
    
    # Se o tar.gz criar uma subpasta (ex: vtxDesktop/vtxDesktop/...), ajustar aqui.
    # Assumindo que o tar.gz extrai os arquivos diretamente ou em uma pasta que o tar trata.
    # Se o tar.gz contiver uma pasta 'vtxDesktop', o comando acima (sem strip) criaria /opt/vortexDesktop/vtxDesktop
    # O usuário disse "baixar e descompactar ... e pronto".
    # Vamos verificar se run.sh está no lugar certo, se não, tentar mover.
    if [ ! -f "$INSTALL_DIR/run.sh" ]; then
        # Tenta encontrar onde foi parar
        FOUND_RUN=$(find "$INSTALL_DIR" -name "run.sh" | head -n 1)
        if [ -n "$FOUND_RUN" ]; then
            log_info "Ajustando estrutura de diretórios..."
            PARENT_DIR=$(dirname "$FOUND_RUN")
            mv "$PARENT_DIR"/* "$INSTALL_DIR/"
            rmdir "$PARENT_DIR"
            chmod +x "$INSTALL_DIR/run.sh"
            chmod +x "$INSTALL_DIR/main.py"
        else
            log_warning "Arquivo run.sh não encontrado após extração. A instalação pode estar incompleta."
        fi
    fi

    log_success "Vortex Desktop instalado em $INSTALL_DIR"
}

# --- Criar Wrapper (/usr/bin/start-vortex) ---
create_binary_wrapper() {
    log_info "Criando wrapper em $BIN_WRAPPER..."
    
    cat <<EOF > "$BIN_WRAPPER"
#! /bin/bash
exec $INSTALL_DIR/run.sh
EOF
    
    chmod +x "$BIN_WRAPPER"
    log_success "Wrapper criado."
}

# --- Configurar Sessão (LightDM/GDM) ---
configure_session() {
    log_info "Configurando sessão X11..."
    
    cat <<EOF > "$SESSION_FILE"
[Desktop Entry]
Name=Vortex Desktop
Comment=Interface Vortex Desktop
Exec=$BIN_WRAPPER
TryExec=$BIN_WRAPPER
Type=Application
DesktopNames=Vortex
X-GDM-Session=true
X-LightDM-DesktopName=Vortex
EOF
    
    log_success "Sessão configurada em $SESSION_FILE"
    
    if ! systemctl is-active --quiet display-manager; then
        log_info "Habilitando LightDM..."
        systemctl enable lightdm >> "$LOG_FILE" 2>&1
        systemctl set-default graphical.target >> "$LOG_FILE" 2>&1
    fi
}

# --- Main ---
main() {
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║      Vortex Desktop - Instalador System-Wide (v2.1)        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    
    check_root
    detect_distro
    
    echo "Resumo da Instalação:"
    echo "  - Distro: $DISTRO"
    echo "  - Destino: $INSTALL_DIR"
    echo "  - Fonte: GitHub Release (v1.1.3)"
    echo "  - Gerenciador de Login: LightDM"
    echo ""
    read -p "Pressione Enter para iniciar a instalação..."

    install_packages
    install_pip_packages
    install_vortex_system
    create_binary_wrapper
    configure_session

    echo ""
    log_success "Instalação Completa! 🎉"
    echo "Para acessar o Vortex Desktop:"
    echo "1. Reinicie o computador"
    echo "2. Na tela de login, selecione 'Vortex Desktop'"
    echo "3. Faça login com seu usuário"
}

main
