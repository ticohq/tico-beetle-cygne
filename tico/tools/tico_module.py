#!/usr/bin/env python3
"""Settings definition and translations for the tico module of Beetle Cygne.

Run after merging upstream. It builds tools/dump_core_options.c against the
core's own libretro_core_options.h, so tico/module/settings.json lists exactly
the options the libnx core reads (wswan_* keys, values and defaults), laid
out in tabs, followed by the overlay's own display and controls options.
Labels are translation keys; the strings go into tico/lang/*.json, taken from
the core's own translations, and from the LABELS, FILL and CHOICES tables below
for what the core does not translate. Choice labels stay English in
settings.json; the overlay translates them through settings_beetle_cygne_value_*
keys.

    python3 tico/tools/tico_module.py
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TICO = ROOT / "tico"
SETTINGS = TICO / "module/settings.json"
LANG_DIR = TICO / "lang"
LANGUAGES = ("en", "de", "es", "fr", "ja", "pt", "ru", "zh")
# tico-nx's own strings label the options it already knew; optional
TICO_NX = Path(os.environ.get("TICO_NX_DIR", ROOT.parents[1] / "tico-nx"))

# Core option -> label key. Options are named after their key without wswan_.
LABEL_KEYS: dict[str, str] = {}

# Core options the frontend has no use for: tico paces the frames itself and
# resamples whatever rate the core runs at (changing it mid-game would leave
# the audio at the old rate).
EXCLUDED = {"wswan_frameskip", "wswan_frameskip_threshold", "wswan_sound_sample_rate"}

# (tab, [(section, [option keys])]). Every core option the dump lists must be
# placed or excluded; the overlay's own tabs are added around these.
LAYOUT = [
    ("settings_beetle_cygne_tab_system", [
        ("settings_beetle_cygne_section_system", ["wswan_language"]),
        ("settings_beetle_cygne_section_owner", [
            "wswan_name_source", "wswan_birth_year", "wswan_birth_month", "wswan_birth_day",
            "wswan_sex", "wswan_blood",
        ]),
    ]),
    ("settings_beetle_cygne_tab_video", [
        ("settings_beetle_cygne_section_display", ["wswan_rotate_display", "wswan_mono_palette",
                                                   "wswan_gfx_colors", "wswan_60hz_mode"]),
    ]),
    ("settings_beetle_cygne_tab_audio", [
        ("settings_beetle_cygne_section_quality", ["wswan_sound_low_pass"]),
    ]),
]

# Listed only while another option has a value, like the core's own menus.
DEPENDS_ON: dict[str, tuple[str, str]] = {}

# Switch buttons a RetroPad button (or the fast-forward hotkey) can sit on.
SWITCH_BUTTONS = [("A", "A"), ("B", "B"), ("X", "X"), ("Y", "Y"), ("L", "L"), ("R", "R"),
                  ("ZL", "ZL"), ("ZR", "ZR"), ("Plus", "Plus"), ("Minus", "Minus"),
                  ("StickL", "Left stick"), ("StickR", "Right stick"), ("Up", "Up"),
                  ("Down", "Down"), ("Left", "Left"), ("Right", "Right"), ("None", "Disabled")]

POSITIONS = [("hidden", "Hidden"), ("top_left", "Top left"), ("top_right", "Top right"),
             ("bottom_left", "Bottom left"), ("bottom_right", "Bottom right")]

# The overlay's own options: how the game is scaled, fast forward and the HUD.
# Shaders are picked in game (Settings > Shaders): tico cannot see the presets
# on the SD card. Fast forward sits on the right stick's click: every other
# button is a WonderSwan button (TicoMain.cpp's UpdateFastForward).
OVERLAY_TAB = ("settings_beetle_cygne_tab_display", [
    ("settings_beetle_cygne_section_screen", [
        {"key": "display_mode", "label": "settings_beetle_cygne_display_mode", "type": "enum",
         "default": "Display", "choices": [("Integer", "Integer"), ("Display", "Display")]},
        {"key": "display_size", "label": "settings_beetle_cygne_display_size", "type": "enum",
         "default": "Original", "choices": [("Stretch", "Stretch"), ("4:3", "4:3"),
                                            ("16:9", "16:9"), ("Original", "Original"),
                                            ("1x", "1x"), ("2x", "2x"), ("Auto", "Auto")]},
    ]),
    ("settings_beetle_cygne_section_fast_forward", [
        {"key": "fast_forward_speed", "label": "settings_beetle_cygne_fast_forward_speed",
         "type": "enum", "default": "200",
         "choices": [("150", "150%"), ("200", "200%"), ("300", "300%"), ("400", "400%"),
                     ("unlimited", "Unlimited")]},
        {"key": "fast_forward_mode", "label": "settings_beetle_cygne_fast_forward_mode",
         "type": "enum", "default": "hold", "choices": [("hold", "Hold"), ("toggle", "Toggle")]},
        {"key": "fast_forward_hotkey", "label": "settings_beetle_cygne_fast_forward_hotkey",
         "type": "enum", "default": "StickR", "choices": SWITCH_BUTTONS},
    ]),
    ("settings_beetle_cygne_section_hud", [
        {"key": "fps_counter_position", "label": "settings_beetle_cygne_fps_counter",
         "type": "enum", "default": "hidden", "choices": POSITIONS},
        {"key": "rendered_ir_position", "label": "settings_beetle_cygne_rendered_resolution",
         "type": "enum", "default": "hidden", "choices": POSITIONS},
    ]),
])

# The overlay's button mapping: each RetroPad button the core reads on a Switch
# button, by default its namesake (TicoMain.cpp's kButtonMappings). The core
# lays the WonderSwan out on them, one way for horizontal games and another
# for vertical ones, so each label says what the button is in both. Rotating
# the key layout is the core's own option, under Controls too.
CONTROLS_TAB = ("settings_beetle_cygne_tab_controls", [
    ("settings_beetle_cygne_section_layout", [
        {"key": "wswan_rotate_keymap"},
    ]),
    ("settings_beetle_cygne_section_button_mapping", [
        {"key": key, "label": "settings_beetle_cygne_" + key, "type": "enum", "default": default,
         "choices": SWITCH_BUTTONS}
        for key, default in [
            ("map_up", "Up"), ("map_right", "Right"), ("map_down", "Down"), ("map_left", "Left"),
            ("map_a", "A"), ("map_b", "B"), ("map_x", "X"), ("map_y", "Y"),
            ("map_l", "L"), ("map_r", "R"), ("map_zl", "ZL"), ("map_zr", "ZR"),
            ("map_start", "Plus"), ("map_select", "Minus"),
        ]
    ] + [
        {"key": "analog_dpad", "label": "settings_beetle_cygne_analog_dpad", "type": "bool",
         "default": "enabled"},
    ]),
])

# Labels the core does not define. key -> (en, de, es, fr, ja, pt, ru, zh)
LABELS = {
    "settings_beetle_cygne_tab_system": ("System", "System", "Sistema", "Système", "システム",
                                         "Sistema", "Система", "系统"),
    "settings_beetle_cygne_section_system": ("System", "System", "Sistema", "Système", "システム",
                                             "Sistema", "Система", "系统"),
    "settings_beetle_cygne_section_owner": ("Owner profile", "Besitzerprofil",
                                            "Perfil del propietario", "Profil du propriétaire",
                                            "オーナー情報", "Perfil do proprietário",
                                            "Профиль владельца", "机主资料"),
    "settings_beetle_cygne_tab_video": ("Video", "Video", "Vídeo", "Vidéo", "ビデオ", "Vídeo",
                                        "Видео", "视频"),
    "settings_beetle_cygne_section_display": ("Display", "Anzeige", "Pantalla", "Affichage", "表示",
                                              "Exibição", "Отображение", "显示"),
    "settings_beetle_cygne_tab_audio": ("Audio", "Audio", "Audio", "Audio", "オーディオ", "Áudio",
                                        "Звук", "音频"),
    "settings_beetle_cygne_section_quality": ("Quality", "Qualität", "Calidad", "Qualité", "品質",
                                              "Qualidade", "Качество", "质量"),
    "settings_beetle_cygne_language": ("Console language", "Konsolensprache",
                                       "Idioma de la consola", "Langue de la console",
                                       "本体の言語", "Idioma do console", "Язык консоли",
                                       "主机语言"),
    "settings_beetle_cygne_name_source": ("Owner name", "Besitzername", "Nombre del propietario",
                                          "Nom du propriétaire", "オーナーの名前",
                                          "Nome do proprietário", "Имя владельца", "机主名称"),
    "settings_beetle_cygne_birth_year": ("Owner birth year", "Geburtsjahr des Besitzers",
                                         "Año de nacimiento", "Année de naissance",
                                         "オーナーの誕生年", "Ano de nascimento",
                                         "Год рождения владельца", "机主出生年份"),
    "settings_beetle_cygne_birth_month": ("Owner birth month", "Geburtsmonat des Besitzers",
                                          "Mes de nacimiento", "Mois de naissance",
                                          "オーナーの誕生月", "Mês de nascimento",
                                          "Месяц рождения владельца", "机主出生月份"),
    "settings_beetle_cygne_birth_day": ("Owner birth day", "Geburtstag des Besitzers",
                                        "Día de nacimiento", "Jour de naissance",
                                        "オーナーの誕生日", "Dia de nascimento",
                                        "День рождения владельца", "机主出生日"),
    "settings_beetle_cygne_sex": ("Owner sex", "Geschlecht des Besitzers", "Sexo del propietario",
                                  "Sexe du propriétaire", "オーナーの性別", "Sexo do proprietário",
                                  "Пол владельца", "机主性别"),
    "settings_beetle_cygne_blood": ("Owner blood type", "Blutgruppe des Besitzers",
                                    "Grupo sanguíneo", "Groupe sanguin", "オーナーの血液型",
                                    "Tipo sanguíneo", "Группа крови владельца", "机主血型"),
    "settings_beetle_cygne_tab_display": ("Display", "Anzeige", "Pantalla", "Affichage", "表示",
                                          "Tela", "Экран", "显示"),
    "settings_beetle_cygne_section_screen": ("Screen", "Bild", "Imagen", "Image", "画面", "Imagem",
                                             "Изображение", "画面"),
    "settings_beetle_cygne_section_hud": ("On-screen info", "Bildschirmanzeige",
                                          "Información en pantalla", "Affichage à l'écran",
                                          "画面表示", "Informações na tela", "Экранная информация",
                                          "屏幕信息"),
    "settings_beetle_cygne_display_mode": ("Display Mode", "Anzeigemodus", "Modo de pantalla",
                                           "Mode d'affichage", "表示モード", "Modo de exibição",
                                           "Режим отображения", "显示模式"),
    "settings_beetle_cygne_display_size": ("Size", "Größe", "Tamaño", "Taille", "サイズ", "Tamanho",
                                           "Размер", "尺寸"),
    "settings_beetle_cygne_fps_counter": ("FPS counter", "FPS-Zähler", "Contador de FPS",
                                          "Compteur de FPS", "FPSカウンター", "Contador de FPS",
                                          "Счётчик FPS", "帧率计数器"),
    "settings_beetle_cygne_rendered_resolution": ("Rendered resolution", "Gerenderte Auflösung",
                                                  "Resolución renderizada", "Résolution de rendu",
                                                  "描画解像度", "Resolução renderizada",
                                                  "Разрешение рендеринга", "渲染分辨率"),
    "settings_beetle_cygne_section_fast_forward": ("Fast Forward", "Vorspulen", "Avance rápido",
                                                   "Avance rapide", "早送り", "Avanço rápido",
                                                   "Перемотка", "快进"),
    "settings_beetle_cygne_fast_forward_speed": ("Fast forward speed", "Vorspul-Geschwindigkeit",
                                                 "Velocidad de avance rápido",
                                                 "Vitesse d'avance rapide", "早送りの速度",
                                                 "Velocidade do avanço rápido",
                                                 "Скорость перемотки", "快进速度"),
    "settings_beetle_cygne_fast_forward_mode": ("Fast forward mode", "Vorspul-Modus",
                                                "Modo de avance rápido", "Mode d'avance rapide",
                                                "早送りモード", "Modo do avanço rápido",
                                                "Режим перемотки", "快进模式"),
    "settings_beetle_cygne_fast_forward_hotkey": ("Fast forward button", "Vorspul-Taste",
                                                  "Botón de avance rápido",
                                                  "Bouton d'avance rapide", "早送りボタン",
                                                  "Botão do avanço rápido", "Кнопка перемотки",
                                                  "快进按键"),
    "settings_beetle_cygne_tab_controls": ("Controls", "Steuerung", "Controles", "Commandes",
                                           "操作", "Controles", "Управление", "控制"),
    "settings_beetle_cygne_section_layout": ("Layout", "Layout", "Disposición", "Disposition",
                                             "配置", "Layout", "Раскладка", "布局"),
    "settings_beetle_cygne_section_button_mapping": ("Button mapping (horizontal / vertical)",
                                                     "Tastenbelegung (horizontal / vertikal)",
                                                     "Asignación de botones (horizontal / vertical)",
                                                     "Attribution des boutons (horizontal / vertical)",
                                                     "ボタン割り当て（横 / 縦）",
                                                     "Mapeamento de botões (horizontal / vertical)",
                                                     "Назначение кнопок (горизонтально / вертикально)",
                                                     "按键映射（横向 / 纵向）"),
    "settings_beetle_cygne_analog_dpad": ("Left stick as D-Pad", "Linker Stick als Steuerkreuz",
                                          "Stick izquierdo como cruceta",
                                          "Stick gauche comme croix directionnelle",
                                          "左スティックを十字キーとして使う",
                                          "Analógico esquerdo como direcional",
                                          "Левый стик как крестовина", "左摇杆作为方向键"),
}

# The mapping's labels: the RetroPad button, then what the WonderSwan has on it
# in horizontal and in vertical games (libretro.c's update_input). The button
# names are the same in every language; "—" is a button a layout leaves unused.
for _key, _pad, _horizontal, _vertical in [
    ("map_up", "D-Pad Up", "X1", "Y2"), ("map_right", "D-Pad Right", "X2", "Y3"),
    ("map_down", "D-Pad Down", "X3", "Y4"), ("map_left", "D-Pad Left", "X4", "Y1"),
    ("map_a", "A", "A", "X3"), ("map_b", "B", "B", "X4"),
    ("map_x", "X", "—", "X2"), ("map_y", "Y", "—", "X1"),
    ("map_l", "L", "Y4", "A"), ("map_r", "R", "Y2", "B"),
    ("map_zl", "ZL", "Y3", "—"), ("map_zr", "ZR", "Y1", "—"),
    ("map_start", "Start", "Start", "Start"),
]:
    LABELS["settings_beetle_cygne_" + _key] = (f"{_pad}: {_horizontal} / {_vertical}",) * 8
LABELS["settings_beetle_cygne_map_select"] = (
    "Select: rotate screen", "Select: Bild drehen", "Select: girar pantalla",
    "Select : pivoter l'écran", "セレクト：画面を回転", "Select: girar tela",
    "Select: повернуть экран", "选择：旋转画面")

# Labels the core leaves empty in some languages, used only where it does.
FILL = {
    "settings_beetle_cygne_rotate_keymap": ("Rotate Button Mappings", "Tastenzuordnungen rotieren",
                                            "Rotar asignación de botones",
                                            "Pivoter l'attribution des boutons",
                                            "ボタン配置を回転", "Rotacionar mapeamento de botões",
                                            "Поворот раскладки кнопок", "旋转按键映射"),
    "settings_beetle_cygne_60hz_mode": ("60Hz Mode", "60-Hz-Modus", "Modo 60 Hz", "Mode 60 Hz",
                                        "60Hzモード", "Modo 60 Hz", "Режим 60 Гц", "60Hz 模式"),
}

# Choice labels the core does not translate. English -> (de, es, fr, ja, pt, ru, zh)
CHOICES = {
    "English": ("Englisch", "Inglés", "Anglais", "英語", "Inglês", "Английский", "英语"),
    "Japanese": ("Japanisch", "Japonés", "Japonais", "日本語", "Japonês", "Японский", "日语"),
    "Frontend Username": ("Benutzername von tico", "Nombre de usuario de tico",
                          "Nom d'utilisateur de tico", "ticoのユーザー名", "Nome de usuário do tico",
                          "Имя пользователя tico", "tico 用户名"),
    "Default (Mednafen)": ("Standard (Mednafen)", "Predeterminado (Mednafen)",
                           "Par défaut (Mednafen)", "デフォルト（Mednafen）", "Padrão (Mednafen)",
                           "По умолчанию (Mednafen)", "默认（Mednafen）"),
    "January": ("Januar", "Enero", "Janvier", "1月", "Janeiro", "Январь", "一月"),
    "February": ("Februar", "Febrero", "Février", "2月", "Fevereiro", "Февраль", "二月"),
    "March": ("März", "Marzo", "Mars", "3月", "Março", "Март", "三月"),
    "April": ("April", "Abril", "Avril", "4月", "Abril", "Апрель", "四月"),
    "May": ("Mai", "Mayo", "Mai", "5月", "Maio", "Май", "五月"),
    "June": ("Juni", "Junio", "Juin", "6月", "Junho", "Июнь", "六月"),
    "July": ("Juli", "Julio", "Juillet", "7月", "Julho", "Июль", "七月"),
    "August": ("August", "Agosto", "Août", "8月", "Agosto", "Август", "八月"),
    "September": ("September", "Septiembre", "Septembre", "9月", "Setembro", "Сентябрь", "九月"),
    "October": ("Oktober", "Octubre", "Octobre", "10月", "Outubro", "Октябрь", "十月"),
    "November": ("November", "Noviembre", "Novembre", "11月", "Novembro", "Ноябрь", "十一月"),
    "December": ("Dezember", "Diciembre", "Décembre", "12月", "Dezembro", "Декабрь", "十二月"),
    "Female": ("Weiblich", "Femenino", "Féminin", "女性", "Feminino", "Женский", "女"),
    "Male": ("Männlich", "Masculino", "Masculin", "男性", "Masculino", "Мужской", "男"),
    "Disabled": ("Deaktiviert", "Desactivado", "Désactivé", "無効", "Desativado", "Выключено",
                 "禁用"),
    "Enabled": ("Aktiviert", "Activado", "Activé", "有効", "Ativado", "Включено", "启用"),
    "Integer": ("Ganzzahlig", "Entero", "Entier", "整数倍", "Inteiro", "Целочисленный", "整数"),
    "Display": ("Anzeige", "Pantalla", "Écran", "画面", "Tela", "Экран", "屏幕"),
    "Stretch": ("Strecken", "Estirar", "Étirer", "引き伸ばし", "Esticar", "Растянуть", "拉伸"),
    "Original": ("Original", "Original", "Original", "オリジナル", "Original", "Оригинал", "原始"),
    "Auto": ("Auto", "Auto", "Auto", "自動", "Auto", "Авто", "自动"),
    "Unlimited": ("Unbegrenzt", "Ilimitado", "Illimité", "無制限", "Ilimitado", "Без ограничений",
                  "无限制"),
    "Hold": ("Halten", "Mantener", "Maintenir", "長押し", "Segurar", "Удерживать", "按住"),
    "Toggle": ("Umschalten", "Alternar", "Basculer", "切り替え", "Alternar", "Переключать", "切换"),
    "Right stick": ("Rechter Stick", "Stick derecho", "Stick droit", "右スティック", "Analógico direito",
                    "Правый стик", "右摇杆"),
    "Left stick": ("Linker Stick", "Stick izquierdo", "Stick gauche", "左スティック", "Analógico esquerdo",
                   "Левый стик", "左摇杆"),
    "Plus": ("Plus", "Más", "Plus", "プラス", "Mais", "Плюс", "加号"),
    "Minus": ("Minus", "Menos", "Moins", "マイナス", "Menos", "Минус", "减号"),
    "Up": ("Oben", "Arriba", "Haut", "上", "Cima", "Вверх", "上"),
    "Down": ("Unten", "Abajo", "Bas", "下", "Baixo", "Вниз", "下"),
    "Left": ("Links", "Izquierda", "Gauche", "左", "Esquerda", "Влево", "左"),
    "Right": ("Rechts", "Derecha", "Droite", "右", "Direita", "Вправо", "右"),
    "Hidden": ("Ausgeblendet", "Oculto", "Masqué", "非表示", "Oculto", "Скрыто", "隐藏"),
    "Top left": ("Oben links", "Arriba a la izquierda", "En haut à gauche", "左上",
                 "Superior esquerdo", "Сверху слева", "左上"),
    "Top right": ("Oben rechts", "Arriba a la derecha", "En haut à droite", "右上",
                  "Superior direito", "Сверху справа", "右上"),
    "Bottom left": ("Unten links", "Abajo a la izquierda", "En bas à gauche", "左下",
                    "Inferior esquerdo", "Снизу слева", "左下"),
    "Bottom right": ("Unten rechts", "Abajo a la derecha", "En bas à droite", "右下",
                     "Inferior direito", "Снизу справа", "右下"),
}

RESTART_SUFFIX = re.compile(r"\s*\((Restart Required|Restart|Reload Core|[^)]*[Nn]eustart[^)]*|[^)]*[Rr]einici[^)]*|"
                            r"[^)]*[Rr]edémarr[^)]*|[^)]*再起動[^)]*|[^)]*перезапуск[^)]*|"
                            r"[^)]*重启[^)]*|[^)]*[Rr]einicializa[^)]*)\)")


def value_key(label: str) -> str:
    """tico_config.cpp's ValueKey: settings_beetle_cygne_value_ + label as a slug."""
    return "settings_beetle_cygne_value_" + "_".join(re.findall(r"[a-z0-9]+", label.lower()))


def clean_label(text: str) -> str:
    return RESTART_SUFFIX.sub("", text).lstrip("> ").strip()


def english_choice(value: str, label: str) -> str:
    # the core leaves on/off style values unlabelled
    return label.capitalize() if label == value and value in ("disabled", "enabled") else label


def dump_options() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / "dump_core_options"
        subprocess.run(["cc", "-std=gnu11", "-w",
                        "-I", str(ROOT),
                        "-I", str(ROOT / "libretro-common/include"),
                        "-o", str(exe), str(Path(__file__).with_name("dump_core_options.c"))],
                       check=True)
        return json.loads(subprocess.run([str(exe)], check=True, capture_output=True,
                                         text=True).stdout)


def label_key(key: str) -> str:
    return LABEL_KEYS.get(key, "settings_beetle_cygne_" + key.removeprefix("wswan_"))


def build_settings(dump: dict) -> dict:
    core = {o["key"]: o for o in dump["en"]}
    # a core option in an overlay tab is written {"key": ...} there
    in_overlay = {o["key"] for _, sections in (OVERLAY_TAB, CONTROLS_TAB)
                  for _, options in sections for o in options if o["key"] in core}
    placed = {key for _, sections in LAYOUT for _, keys in sections for key in keys} | in_overlay
    missing = sorted(set(core) - placed - EXCLUDED)
    if missing:
        raise SystemExit(f"core options not placed in LAYOUT: {missing}")

    def core_option(key):
        source = core[key]
        values = [v for v, _ in source["values"]]
        option = {"key": key, "label": label_key(key)}
        if sorted(values) == ["disabled", "enabled"]:
            option.update(type="bool", default=source["default"])
        else:
            option.update(type="enum", default=source["default"], choices=[
                {"label": english_choice(v, l), "value": v} for v, l in source["values"]])
        if RESTART_SUFFIX.search(source["desc"]):
            option["restart"] = True
        if key in DEPENDS_ON:
            on, value = DEPENDS_ON[key]
            option["depends_on"] = {"key": on, "value": value}
        return option

    tabs = [{"name": tab, "sections": [{"title": title, "options": [core_option(k) for k in keys]}
                                       for title, keys in sections]}
            for tab, sections in LAYOUT]

    def overlay_option(o):
        if o["key"] in core:
            return core_option(o["key"])
        if "choices" in o:
            return {**o, "choices": [{"label": l, "value": v} for v, l in o["choices"]]}
        return dict(o)

    def overlay_tab(definition):
        tab, sections = definition
        return {"name": tab, "sections": [
            {"title": title, "options": [overlay_option(o) for o in options]}
            for title, options in sections]}

    tabs.insert(1, overlay_tab(OVERLAY_TAB))
    tabs.append(overlay_tab(CONTROLS_TAB))

    return {
        "core_id": "beetle_cygne",
        "display_name": "Beetle Cygne",
        "config_file": "beetle_cygne.jsonc",
        "slugs": ["ws", "wsc"],
        "bool_true_value": "enabled",
        "bool_false_value": "disabled",
        "tabs": tabs,
    }


def tico_owned(key: str) -> bool:
    """Labels tico itself defines, whose wording tico keeps."""
    return key in LABEL_KEYS.values() or key.startswith(("settings_beetle_cygne_tab_",
                                                          "settings_beetle_cygne_section_"))


def build_strings(dump: dict, settings: dict,
                  existing: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    strings: dict[str, dict[str, str]] = {lang: {} for lang in LANGUAGES}
    english = {o["key"]: o for o in dump["en"]}
    for lang in LANGUAGES:
        out = strings[lang]
        index = LANGUAGES.index(lang)
        for option in dump[lang]:
            if option["key"] in EXCLUDED or option["key"] not in english:
                continue
            key, en = option["key"], english[option["key"]]
            # a language the core leaves empty falls back (FILL, then English)
            if clean_label(option["desc"]):
                out[label_key(key)] = clean_label(option["desc"])
            # by value: a translation may list the choices differently
            en_labels = dict(en["values"])
            for value, label in option["values"]:
                if label is None or value not in en_labels:
                    continue
                en_text = english_choice(value, en_labels[value])
                if label != en_labels[value]:
                    out[value_key(en_text)] = label
        for key, texts in LABELS.items():
            out[key] = texts[index]
        for key, texts in FILL.items():
            out.setdefault(key, texts[index])
        if lang != "en":
            for choice, translations in CHOICES.items():
                out[value_key(choice)] = translations[index - 1]
        if lang == "en":
            for key in list(out):
                if key.startswith("settings_beetle_cygne_value_"):
                    del out[key]
    # tico's own labels keep tico's wording: from tico-nx when it is checked
    # out, otherwise as the language files already have them
    for lang in LANGUAGES:
        path = TICO_NX / "assets/lang" / f"{lang}.json"
        source = json.loads(path.read_text()) if path.exists() else existing[lang]
        for key, value in source.items():
            if tico_owned(key):
                strings[lang][key] = value
    used = set()

    def walk(node):
        if isinstance(node, dict):
            for field in ("label", "name", "title"):
                if isinstance(node.get(field), str) and node[field].startswith("settings_"):
                    used.add(node[field])
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)

    walk(settings)
    unlabelled = sorted(used - set(strings["en"]))
    if unlabelled:
        raise SystemExit(f"labels without English text: {unlabelled}")
    return strings


def main() -> None:
    dump = dump_options()
    settings = build_settings(dump)
    SETTINGS.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
    current_files = {lang: json.loads((LANG_DIR / f"{lang}.json").read_text())
                     if (LANG_DIR / f"{lang}.json").exists() else {} for lang in LANGUAGES}
    for lang, strings in build_strings(dump, settings, current_files).items():
        path = LANG_DIR / f"{lang}.json"
        current = {k: v for k, v in current_files[lang].items()
                   if not k.startswith("settings_beetle_cygne_")}
        current.update(dict(sorted(strings.items())))
        path.write_text(json.dumps(current, indent=4, ensure_ascii=False) + "\n")
    print(f"wrote {SETTINGS.relative_to(ROOT)} and {len(LANGUAGES)} language files")


if __name__ == "__main__":
    main()
