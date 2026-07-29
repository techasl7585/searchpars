from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemAction:
    title: str
    description: str
    commands: tuple[tuple[str, ...], ...]
    icon: str


ACTIONS: dict[str, SystemAction] = {
    "bluetooth_on": SystemAction(
        "Bluetooth'u aç",
        "Bluetooth bağdaştırıcısını etkinleştir",
        (("bluetoothctl", "power", "on"),),
        "bluetooth-active-symbolic",
    ),
    "bluetooth_off": SystemAction(
        "Bluetooth'u kapat",
        "Bluetooth bağdaştırıcısını devre dışı bırak",
        (("bluetoothctl", "power", "off"),),
        "bluetooth-disabled-symbolic",
    ),
    "wifi_on": SystemAction(
        "Wi‑Fi'yi aç",
        "Kablosuz ağı etkinleştir",
        (("nmcli", "radio", "wifi", "on"),),
        "network-wireless-signal-excellent-symbolic",
    ),
    "wifi_off": SystemAction(
        "Wi‑Fi'yi kapat",
        "Kablosuz ağı devre dışı bırak",
        (("nmcli", "radio", "wifi", "off"),),
        "network-wireless-offline-symbolic",
    ),
    "screenshot": SystemAction(
        "Ekran görüntüsü al",
        "Pardus ekran görüntüsü aracını çalıştır",
        (
            ("xfce4-screenshooter",),
            ("gnome-screenshot", "-i"),
            ("spectacle",),
        ),
        "applets-screenshooter-symbolic",
    ),
    "mute": SystemAction(
        "Sesi kapat",
        "Sistem sesini sessize al",
        (
            ("pactl", "set-sink-mute", "@DEFAULT_SINK@", "1"),
            ("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "1"),
        ),
        "audio-volume-muted-symbolic",
    ),
    "unmute": SystemAction(
        "Sesi aç",
        "Sistem sesini etkinleştir",
        (
            ("pactl", "set-sink-mute", "@DEFAULT_SINK@", "0"),
            ("wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "0"),
        ),
        "audio-volume-high-symbolic",
    ),
    "open_trash": SystemAction(
        "Çöp kutusunu aç",
        "Dosya yöneticisinde çöp kutusunu göster",
        (("xdg-open", "trash:///"),),
        "user-trash-symbolic",
    ),
    "open_settings": SystemAction(
        "Ayarları aç",
        "Pardus sistem ayarlarını göster",
        (
            ("xfce4-settings-manager",),
            ("gnome-control-center",),
            ("systemsettings",),
        ),
        "preferences-system-symbolic",
    ),
}


def run_action(action_key: str) -> tuple[bool, str]:
    action = ACTIONS.get(action_key)
    if not action:
        return False, "Bilinmeyen işlem"

    last_error = ""
    for command in action.commands:
        if not shutil.which(command[0]):
            continue
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if completed.returncode == 0:
                return True, f"{action.title} işlemi tamamlandı."
            last_error = completed.stderr.strip() or completed.stdout.strip()
        except (OSError, subprocess.SubprocessError) as exc:
            last_error = str(exc)
    return False, last_error or "Bu işlem için gerekli sistem aracı bulunamadı."
